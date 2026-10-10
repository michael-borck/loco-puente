"""llama.cpp — GGUF inference with explicit control over where weights live.

The alternative to Ollama, and the reason this backend exists is one flag:
`--cpu-moe`. It keeps a MoE model's routed experts in system RAM while
attention, KV cache and shared experts stay in VRAM. Experts activate on only a
few percent of tokens, so the RAM path is not a bottleneck — and the result is
that a large MoE model can occupy LESS VRAM than a small dense one. On a card
shared with ComfyUI, SwarmUI, Voicebox and a song model, that is the difference
between coexisting and thrashing.

Ollama, vLLM and SGLang do not offer this. vLLM and SGLang are built around
tensor parallelism; neither has expert-aware CPU offload. So "move to vLLM" and
"get the MoE trick" are mutually exclusive — this backend is the one that keeps
the trick.

One `llama-server` serves one model, so several models means several instances,
each on its own port. That mirrors Ollama's shape on purpose: the two are meant
to be swappable, and matching the config shape is what makes that cheap.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from puente.models import LlamaCppConfig, LlamaCppInstance, ServiceConfig

from .base import ServiceBase

#: Official upstream image. Rebuilt nightly against main, so it tracks llama.cpp
#: closely — which matters, because the MoE offload flags are still moving.
IMAGE = "ghcr.io/ggml-org/llama.cpp:server-cuda"


def _models_dir(config: LlamaCppConfig, data_dir: str) -> str:
    """Host directory holding the GGUF files."""
    return config.models_dir or os.path.join(data_dir, "llama.cpp", "models")


def _gguf_filename(inst: LlamaCppInstance) -> str:
    """The file llama-server will be pointed at.

    A bare name gains the .gguf suffix people habitually omit. `hf_file` wins
    over `model` when both are set, because it is the unambiguous one.
    """
    if inst.hf_file:
        return inst.hf_file
    name = inst.model or ""
    if name and not name.endswith(".gguf"):
        name += ".gguf"
    return name


def build_command(inst: LlamaCppInstance, port: int) -> list[str]:
    """The llama-server argv for one instance.

    Kept as a pure function so the flag construction is testable without a GPU —
    which matters, because a wrong flag here silently costs VRAM rather than
    crashing.
    """
    args = [
        "-m",
        f"/models/{_gguf_filename(inst)}",
        "--host", "0.0.0.0",
        "--port", str(port),
        "-c", str(inst.ctx),
        "-np", str(inst.parallel),
    ]

    # -ngl 999 offloads everything; a lower count is the explicit way to leave
    # room for whatever else shares the card.
    ngl = 999 if inst.n_gpu_layers == "all" else int(inst.n_gpu_layers)
    args += ["-ngl", str(ngl)]

    # --cpu-moe N: routed experts of the first N layers to system RAM.
    if inst.cpu_moe is not None:
        args += ["-ncmoe", "999" if inst.cpu_moe == "all" else str(int(inst.cpu_moe))]

    if inst.alias:
        args += ["-a", inst.alias]

    # Turn reasoning off for classroom Q&A. Sent on the OpenAI endpoint as
    # reasoning_effort: none; measured ~5x latency for no gain there.
    if inst.disable_thinking:
        args += ["--reasoning-budget", "0"]

    args += list(inst.extra_args)
    return args


class LlamaCppService(ServiceBase):
    name = "llama_cpp"
    description = "GGUF inference with MoE expert offload to system RAM"
    default_port = 8081
    install_method = "docker"
    docker_image = IMAGE
    requires_gpu = True

    def compose_volumes(self, config: ServiceConfig) -> dict[str, dict[str, Any]]:
        cfg = config if isinstance(config, LlamaCppConfig) else LlamaCppConfig()
        # Every instance keeps its own container-level HF cache, so a model
        # fetched by one is not invisible to another.
        return {f"llama-cpp-{_slug(i.name)}-hf": {} for i in cfg.instances}

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        cfg = config if isinstance(config, LlamaCppConfig) else LlamaCppConfig()
        instances = cfg.instances
        if not instances:
            return None

        models_dir = _models_dir(cfg, data_dir)
        services: dict[str, Any] = {}

        for inst in instances:
            name = _slug(inst.name)
            port = inst.port or cfg.default_port
            slug = f"llama-cpp-{name}"

            svc: dict[str, Any] = {
                "image": self.docker_image,
                "container_name": f"puente-{slug}",
                "command": build_command(inst, port),
                "ports": [f"{port}:{port}"],
                "volumes": [
                    f"{models_dir}:/models:ro",
                    f"{slug}-hf:/root/.cache/huggingface",
                ],
                # No auth: llama-server has none, and it exposes whatever model
                # is loaded. Bind to the bridge and let Caddy + bearer auth front
                # it, the same contract the other API services have.
                "restart": "unless-stopped",
            }

            deploy = self.gpu_reservation(inst.gpu)
            if deploy:
                svc["deploy"] = deploy

            # A model that is still downloading answers nothing, and Docker would
            # kill a slow first start. Loading a large GGUF off disk takes
            # minutes on a cold page cache.
            svc["healthcheck"] = {
                "test": [
                    "CMD-SHELL",
                    f"curl -sf http://localhost:{port}/health || exit 1",
                ],
                "interval": "30s",
                "timeout": "10s",
                "start_period": "600s",
                "retries": 3,
            }

            services[slug] = svc

        return services

    def pre_start(self, config: ServiceConfig, data_dir: str) -> None:
        """Create the models directory, and warn about a model that isn't there.

        A missing GGUF is not a build error — llama-server starts and then fails
        on the first request, which is a confusing way to learn a file is absent.
        """
        cfg = config if isinstance(config, LlamaCppConfig) else LlamaCppConfig()
        models_dir = Path(_models_dir(cfg, data_dir))
        models_dir.mkdir(parents=True, exist_ok=True)

        present = {p.name for p in models_dir.glob("*.gguf")}
        for inst in cfg.instances:
            wanted = _gguf_filename(inst)
            if inst.hf_file:
                continue  # fetched on first use; nothing to check yet
            if wanted and wanted not in present:
                print(
                    f"  ⚠ llama.cpp[{inst.name}]: {wanted} is not in {models_dir}. "
                    f"Place the GGUF there, or set hf_repo/hf_file to fetch it."
                )


def _slug(name: str) -> str:
    """Compose-safe service name from an instance name."""
    return name.strip().lower().replace("_", "-").replace(" ", "-") or "primary"