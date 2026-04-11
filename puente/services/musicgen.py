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
    # Community Gradio wrapper around Meta's AudioCraft / MusicGen.
    # Verify the tag and image source before pinning for production —
    # community AudioCraft images come and go, and you may want to swap
    # to a self-built image or a different community wrapper over time.
    docker_image = "ghcr.io/audiocraftplus/audiocraft-plus:latest"
    requires_gpu = True

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = dict(config.environment)

        fragment: dict[str, Any] = {
            "musicgen": {
                "image": self.docker_image,
                "container_name": "puente-musicgen",
                "ports": [f"{port}:7860"],
                "volumes": [
                    f"{data_dir}/musicgen:/data",
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
