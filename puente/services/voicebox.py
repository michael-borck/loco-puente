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

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = {"LOG_LEVEL": "info", "NUMBA_CACHE_DIR": "/tmp/numba_cache"}
        env.update(config.environment)

        return {
            "voicebox": {
                "build": {"context": "https://github.com/jamiepine/voicebox.git"},
                "container_name": "puente-voicebox",
                "ports": [f"{port}:17493"],
                "volumes": [
                    f"{data_dir}/voicebox/output:/app/data/generations",
                    f"{data_dir}/voicebox/data:/app/data",
                    f"{data_dir}/voicebox/hf-cache:/home/voicebox/.cache/huggingface",
                ],
                "environment": env,
                "restart": "unless-stopped",
            }
        }
