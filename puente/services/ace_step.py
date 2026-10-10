"""ACE-Step 1.5 — lyrics-to-song generation.

Chosen over YuE for a stack that shares its GPU: ACE-Step's 2B variant is ~4.7 GB
of weights and generates a full song in under 10 seconds on an RTX 3090, where
YuE needs 24 GB of BF16 and runs at 0.083x real-time — *slower than realtime*, and
188x slower than ACE-Step on the same card. For a student-facing service the
smaller, faster model is the one that can coexist with everything else.

Its own service rather than a ComfyUI custom node, and the reason is a version
conflict rather than tidiness: ACE-Step pins torch 2.10.0+cu128 while the ComfyUI
image carries 2.6.0+cu124. They cannot share a venv. Separate container, separate
torch, separate GPU pin, separate healthcheck.

Exposes the REST API on :8002. The official ComfyUI node
(ace-step/ACE-Step-ComfyUI) is a *client* of this server, so it can be pointed at
it later without changing anything here.
"""

from __future__ import annotations

from typing import Any

from puente.models import AceStepConfig, ServiceConfig

from .base import ServiceBase


class AceStepService(ServiceBase):
    name = "ace_step"
    description = "Song generation from lyrics (ACE-Step 1.5)"
    default_port = 8002
    install_method = "docker"
    # Built from upstream's own Dockerfile, which is the supported install path
    # (it uses `uv sync` against a committed lockfile). Upstream publishes no
    # image, so this builds from a git context — same shape as voicebox.
    docker_image = None
    # Off by default. This is a VRAM decision, not a capability one: the 2b
    # variant is cheap, but a card already holding ComfyUI, Voicebox and Ollama
    # is not free, and the operator should choose when.
    requires_gpu = True

    REPO = "ace-step/ACE-Step-1.5"

    #: Puente's variant name -> upstream's ACESTEP_CONFIG_PATH.
    #:
    #: An explicit map, not string interpolation. Upstream names the 2B family
    #: "acestep-v15-turbo" and the 4B family "acestep-v15-xl-turbo" — there is no
    #: "acestep-v15-2b-turbo", and a config name that does not exist sends the
    #: first request looking for a model that is never downloadable.
    CONFIG_PATHS = {
        "2b": "acestep-v15-turbo",
        "xl": "acestep-v15-xl-turbo",
    }

    def _build_context(self, config: AceStepConfig) -> str:
        """Git build context, pinned by commit.

        A branch would make the built image non-reproducible, which is the same
        trap voicebox's build_ref documents — see ADR0009.
        """
        return f"https://github.com/{self.REPO}.git#{config.build_ref or 'main'}"

    def compose_volumes(self, config: ServiceConfig) -> dict[str, dict[str, Any]]:
        # Checkpoints are large and are the thing an operator wants to keep, so
        # bind-mounted rather than kept in an anonymous volume. Outputs likewise.
        return {}

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        cfg = config if isinstance(config, AceStepConfig) else AceStepConfig()
        port = cfg.port or self.default_port

        env: dict[str, str] = {
            # Every name below is taken from upstream's .env.example. Inventing
            # an env var here would produce a knob that looks live and does
            # nothing — worse than no knob.
            #
            # 2b is ~4.7GB of weights and coexists with the rest of the stack;
            # xl is the 4B DiT at ~9GB, needing >=12GB free with offload.
            "ACESTEP_CONFIG_PATH": self.CONFIG_PATHS[cfg.variant],
            "ACESTEP_LM_MODEL_PATH": cfg.lm_model,
            "ACESTEP_DEVICE": "cuda",
            # The LM adds thinking mode, CoT captioning and sample mode. On a
            # card shared with ComfyUI it is also the first thing to go, so it
            # follows `resident` rather than defaulting on.
            "ACESTEP_INIT_LLM": "true" if cfg.resident else "false",
            # vLLM is faster but claims VRAM of its own; pt is the lighter
            # backend and the right default beside other services.
            "ACESTEP_LM_BACKEND": cfg.lm_backend,
            "ACESTEP_CHECKPOINTS_DIR": "/app/checkpoints",
        }
        env.update(cfg.environment)

        service: dict[str, Any] = {
            "build": {"context": self._build_context(cfg)},
            "container_name": "puente-ace-step",
            "ports": [f"{port}:{port}"],
            "volumes": [
                f"{data_dir}/ace-step/checkpoints:/app/checkpoints",
                f"{data_dir}/ace-step/outputs:/app/outputs",
            ],
            "environment": env,
            "restart": "unless-stopped",
            "healthcheck": {
                "test": ["CMD-SHELL", f"curl -sf http://localhost:{port}/health || exit 1"],
                "interval": "30s",
                "timeout": "10s",
                # First start downloads weights and loads the model. Minutes, not
                # seconds — without this Docker kills it mid-download.
                "start_period": "600s",
                "retries": 3,
            },
        }

        deploy = self.gpu_reservation(cfg.gpu)
        if deploy:
            service["deploy"] = deploy

        return {"ace-step": service}

    def pre_start(self, config: ServiceConfig, data_dir: str) -> None:
        """Create the bind-mount directories before Docker does.

        Docker creates a missing bind source as root, and this container runs as
        a non-root user, so a root-owned checkpoints dir is unwritable — the
        same trap the ComfyUI /basedir dirs have.
        """
        from pathlib import Path

        base = Path(data_dir) / "ace-step"
        for sub in ("checkpoints", "outputs"):
            (base / sub).mkdir(parents=True, exist_ok=True)