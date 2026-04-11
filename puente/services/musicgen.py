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
    # Pull-first, build-fallback. The image is built and pushed by the
    # .github/workflows/build-images.yml workflow on changes to
    # puente/dockerfiles/musicgen/Dockerfile. If the image isn't available
    # (forks, dev, first run before CI lands) docker compose falls back to
    # the bundled Dockerfile via the `build:` directive below.
    docker_image = "ghcr.io/michael-borck/puente-musicgen:latest"
    requires_gpu = True

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = dict(config.environment)

        fragment: dict[str, Any] = {
            "musicgen": {
                "image": self.docker_image,
                "build": {"context": "./dockerfiles/musicgen"},
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
