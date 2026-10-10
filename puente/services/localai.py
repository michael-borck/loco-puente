"""LocalAI — the default inference engine (ADR0012).

LocalAI is a single Go server that speaks OpenAI-, Anthropic- and
ElevenLabs-compatible APIs across 60+ backends, and installs backends on the fly
as OCI bundles. It replaces the *engine* slot: text, image, voice, embedding and
(through its backends) ACE-Step all come from one process.

It is not an orchestrator. It does not manage sibling containers, a reverse
proxy, or per-service lifecycles — which is why it sits inside the stack rather
than replacing it.

Two things LocalAI does *not* do, and which is why `decide.py` and `capabilities.py`
still exist rather than being deleted in favour of upstream:

  * it needs an engine to be running, so the no-engine path (nothing installed,
    no VRAM, no network) still has to be ours — see `LexicalBackend`;
  * it does not know what an *operator's* box can afford.

The GPU pin is set with the standard `nvidia` runtime env rather than a compose
`deploy:` block. LocalAI is a fat container and `deploy.resources` only applies
under swarm, which is not how this stack runs — the env var works under plain
`docker compose up`, which is what compose.py generates.
"""

from __future__ import annotations

from typing import Any

from puente.models import LocalAIConfig, ServiceConfig

from .base import ServiceBase

#: Upstream image. Pinned to a release rather than `latest` — see ADR0012's note
#: on reproducibility, and `puente doctor`'s ability to say what is running.
IMAGE = "docker.io/mudler/localai:v3.5.0"


def build_command(config: LocalAIConfig) -> list[str]:
    """The `local-ai run` argv.

    A pure function so the flags are testable without a GPU. A wrong flag here is
    not a crash — LocalAI starts anyway with different behaviour, so it is worth
    asserting on directly.
    """
    args = ["--models-path", config.models_dir or "/models"]

    # Backends are installed on demand as OCI bundles. Preloading them makes a
    # cold start deterministic instead of "the first request of the day decides
    # which backend exists", which matters when the box may have no internet.
    if config.backends:
        args += ["--preload-backend", ",".join(config.backends)]

    if config.context_size:
        args += ["--context-size", str(config.context_size)]
    if config.parallel:
        args += ["--parallel", str(config.parallel)]
    if config.gpu_layers is not None:
        args += ["--gpus", str(config.gpu_layers)]
    if config.threads:
        args += ["--threads", str(config.threads)]
    if config.debug:
        args += ["--debug"]

    args += list(config.extra_args)
    return args


class LocalAIService(ServiceBase):
    name = "localai"
    description = "Local AI engine — OpenAI-compatible API across 60+ backends"
    default_port = 8080
    install_method = "docker"
    docker_image = IMAGE
    #: False, unlike the other engines: LocalAI runs CPU-only. Marking it
    #: GPU-required would make `puente init` skip it on a box with no NVIDIA
    #: card, where it still works — just slowly.
    requires_gpu = False

    def compose_volumes(self, config: ServiceConfig) -> dict[str, dict[str, Any]]:
        cfg = config if isinstance(config, LocalAIConfig) else LocalAIConfig()
        # Models are the point of the service; a container without a volume for
        # them re-downloads gigabytes on every recreate.
        if cfg.models_dir and cfg.models_dir != "default":
            return {}
        return {"localai-models": {}}

    def compose_fragment(
        self, config: ServiceConfig, data_dir: str
    ) -> dict[str, Any] | None:
        if getattr(config, "install_method", "docker") != "docker":
            return None

        cfg = config if isinstance(config, LocalAIConfig) else LocalAIConfig()
        port = cfg.port or self.default_port

        env = {"LOCALAI_HOST": "0.0.0.0:8080"}
        env.update(cfg.environment)
        env.update(config.environment)

        # Models dir: an operator's existing library wins, so someone with 211 GB
        # of GGUFs already on disk is not told to re-download them.
        if cfg.models_dir and cfg.models_dir != "default":
            volumes = [f"{cfg.models_dir}:/models"]
        else:
            volumes = ["localai-models:/models"]

        service: dict[str, Any] = {
            "image": self.docker_image,
            "container_name": "puente-localai",
            "ports": [f"{port}:8080"],
            "volumes": volumes,
            "environment": env,
            "command": build_command(cfg),
            "restart": "unless-stopped",
        }

        # CUDA is opt-in. LocalAI runs CPU-only without this, and a host with no
        # NVIDIA card should get a working — if slow — engine rather than a
        # container that refuses to start.
        if cfg.cuda:
            gpu = str(config.gpu) if config.gpu is not None else "0"
            env["CUDA_VISIBLE_DEVICES"] = gpu
            env["NVIDIA_VISIBLE_DEVICES"] = gpu

        return {"localai": service}
