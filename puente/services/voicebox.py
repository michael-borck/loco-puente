"""Voicebox — local voice cloning / TTS studio (under evaluation)."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class VoiceboxService(ServiceBase):
    name = "voicebox"
    description = "Local voice cloning + TTS studio (ElevenLabs alternative)"
    default_port = 17493
    install_method = "docker"
    # Upstream ships a multi-stage Dockerfile that copies from its own repo
    # layout, so we let Compose build directly from the upstream git context
    # rather than maintaining a parallel Dockerfile under dockerfiles/.
    docker_image = None
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

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = {
            "LOG_LEVEL": "info",
            "NUMBA_CACHE_DIR": "/tmp/numba_cache",
            "HF_HOME": "/app/data/hf-cache",
        }
        env.update(config.environment)

        return {
            "voicebox": {
                "build": {"context": "https://github.com/jamiepine/voicebox.git"},
                "container_name": "puente-voicebox",
                "ports": [f"{port}:17493"],
                "volumes": ["voicebox-data:/app/data"],
                "environment": env,
                "restart": "unless-stopped",
            }
        }
