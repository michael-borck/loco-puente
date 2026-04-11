"""MusicGen — local music generation via AudioCraft (Docker, GPU)."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class MusicGenService(ServiceBase):
    name = "musicgen"
    description = "Local music generation (MusicGen / AudioCraft)"
    default_port = 7860
    install_method = "docker"
    # Built locally from puente/dockerfiles/musicgen — Meta's AudioCraft has
    # no published Docker image, so we wrap their bundled Gradio demo.
    docker_image = None
    requires_gpu = True

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = dict(config.environment)

        fragment: dict[str, Any] = {
            "musicgen": {
                "build": {"context": "./dockerfiles/musicgen"},
                "image": "puente-musicgen:local",
                "container_name": "puente-musicgen",
                "ports": [f"{port}:7860"],
                "volumes": [
                    f"{data_dir}/musicgen:/root/.cache/huggingface",
                ],
                "environment": env,
                "restart": "unless-stopped",
            }
        }

        if config.gpu is not None:
            fragment["musicgen"]["deploy"] = {
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
