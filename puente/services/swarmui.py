"""SwarmUI — friendly image-gen front-end that uses ComfyUI as the backend."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class SwarmUIService(ServiceBase):
    name = "swarmui"
    description = "Friendly image generation UI (uses ComfyUI backend)"
    default_port = 7801
    install_method = "docker"
    # Community-maintained image from SwarmUI's author (mcmonkey4eva).
    # SwarmUI launches its own ComfyUI bundle by default. We point it at
    # the existing puente-comfyui container so it reuses the running GPU
    # instance and the already-downloaded checkpoints (no model
    # duplication, no extra VRAM usage).
    docker_image = "ghcr.io/mcmonkey4eva/swarmui:latest"
    requires_gpu = True

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = {
            # Tell SwarmUI to talk to the existing ComfyUI container on the
            # puente network instead of spinning up its own bundled instance.
            "SWARMUI_BACKEND_COMFYUI_URL": "http://puente-comfyui:8188",
        }
        env.update(config.environment)

        fragment: dict[str, Any] = {
            "swarmui": {
                "image": self.docker_image,
                "container_name": "puente-swarmui",
                "ports": [f"{port}:7801"],
                "volumes": [
                    f"{data_dir}/swarmui:/SwarmUI/Data",
                ],
                "environment": env,
                "restart": "unless-stopped",
            }
        }

        if config.gpu is not None:
            fragment["swarmui"]["deploy"] = {
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
