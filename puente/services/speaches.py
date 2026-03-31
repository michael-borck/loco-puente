"""Speaches — local TTS/STT (OpenAI Audio API compatible)."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class SpeachesService(ServiceBase):
    name = "speaches"
    description = "Voice: speech-to-text (Whisper) and text-to-speech (Kokoro)"
    default_port = 8000
    install_method = "docker"
    docker_image = "ghcr.io/speaches-ai/speaches:latest-cuda"
    requires_gpu = True

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = dict(config.environment)

        fragment: dict[str, Any] = {
            "speaches": {
                "image": self.docker_image,
                "container_name": "puente-speaches",
                "ports": [f"{port}:8000"],
                "volumes": [f"{data_dir}/speaches:/root/.cache"],
                "environment": env,
                "restart": "unless-stopped",
            }
        }

        if config.gpu is not None:
            fragment["speaches"]["deploy"] = {
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

        return fragment
