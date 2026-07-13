"""Voicebox — local voice cloning / TTS studio (under evaluation)."""

from __future__ import annotations

import subprocess
from typing import Any

from rich.console import Console

from puente.models import ServiceConfig, VoiceboxConfig

from .base import ServiceBase

console = Console()

UPSTREAM_REPO = "jamiepine/voicebox"


class VoiceboxService(ServiceBase):
    name = "voicebox"
    description = "Local voice cloning + TTS studio (ElevenLabs alternative)"
    default_port = 17493
    install_method = "docker"
    # Upstream ships a multi-stage Dockerfile that copies from its own repo
    # layout, so we let Compose build directly from the upstream git context
    # rather than maintaining a parallel Dockerfile under dockerfiles/.
    docker_image = None
    # Runs fine on CPU, but its bundled torch is a cu130 build and will use a
    # GPU if one is handed to it — no extra CUDA libs needed (voicebox's own
    # /backend/download-cuda is unnecessary). Set `gpu:` in puente.yml to pin
    # it to a card. cu130 wheels need host driver >= 580.
    requires_gpu = False

    # Voicebox is the only puente service that runs as a non-root user inside
    # the container (USER voicebox in upstream's Dockerfile). Bind mounts
    # would require world-writable host dirs to be usable from inside; named
    # Docker volumes sidestep that — Docker manages permissions and the
    # in-container voicebox user owns its own data.
    #
    # We use a single named volume mounted at /app/data because that path is
    # explicitly created and chown'd to voicebox:voicebox in the upstream
    # Dockerfile. HF cache is redirected (via HF_HOME) into a subdirectory
    # of that volume so it inherits the same correct permissions, instead of
    # mounting a second volume at /home/voicebox/.cache/huggingface where the
    # path doesn't exist in the image and Docker creates it as root.
    #
    # To grab generated audio off the host:
    #   docker cp puente-voicebox:/app/data/generations ./voicebox-output

    def compose_volumes(self, config: ServiceConfig) -> dict[str, dict[str, Any]]:
        return {"voicebox-data": {}}

    @staticmethod
    def _build_context(config: ServiceConfig) -> str:
        """Compose git build context, honouring an optional owner/repo@ref override."""
        build_ref = getattr(config, "build_ref", None) or UPSTREAM_REPO
        repo, _, ref = build_ref.partition("@")
        context = f"https://github.com/{repo}.git"
        # Compose selects a branch/tag/commit with a '#fragment' on the git URL.
        return f"{context}#{ref}" if ref else context

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = {
            "LOG_LEVEL": "info",
            "NUMBA_CACHE_DIR": "/tmp/numba_cache",
            "HF_HOME": "/app/data/hf-cache",
        }

        # Unload idle models so a dormant voicebox stops pinning the card. Stock
        # upstream has no idle unloading (jamiepine/voicebox#889), so only set
        # this when building from a fork that can actually honour it -- otherwise
        # it is a knob that looks live and silently does nothing.
        if getattr(config, "build_ref", None):
            env["VOICEBOX_IDLE_UNLOAD_SECONDS"] = "600"

        env.update(config.environment)

        service: dict[str, Any] = {
            "build": {"context": self._build_context(config)},
            "container_name": "puente-voicebox",
            "ports": [f"{port}:17493"],
            "volumes": ["voicebox-data:/app/data"],
            "environment": env,
            "restart": "unless-stopped",
        }

        if config.gpu is not None:
            service["deploy"] = {
                "resources": {
                    "reservations": {
                        "devices": [
                            {
                                "driver": "nvidia",
                                "device_ids": [str(config.gpu)],
                                "capabilities": ["gpu"],
                            }
                        ]
                    }
                }
            }

        return {"voicebox": service}

    def pre_start(self, config: ServiceConfig, data_dir: str) -> None:
        """Warn that the first `up` compiles voicebox from source.

        Unlike most puente services there is no image to pull — upstream ships a
        Dockerfile but publishes no image, so Compose builds it here. That build
        pulls a full torch/CUDA stack and takes a long time, with no output for
        minutes at a stretch. Say so up front, or a first-time user reasonably
        concludes it has hung. Only fires when the image is genuinely absent, so
        routine restarts stay quiet.
        """
        try:
            probe = subprocess.run(
                ["docker", "image", "inspect", "puente-voicebox"],
                capture_output=True,
                timeout=10,
            )
            built = probe.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return  # no docker / can't tell — compose will surface any real error

        if built:
            return

        console.print(
            "  [yellow]First run:[/yellow] voicebox has no prebuilt image, so it is "
            "compiled from source now\n"
            "  (torch + CUDA — expect [bold]10-20 minutes[/bold] and long silent "
            "stretches). This is a [bold]one-off[/bold];\n"
            "  later starts reuse the built image and come up in seconds."
        )
