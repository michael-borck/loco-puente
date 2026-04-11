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
    # Pull-first, build-fallback. Built and pushed to GHCR by the
    # .github/workflows/build-images.yml workflow. Configure SwarmUI to
    # talk to the existing puente-comfyui container instead of spinning
    # up its own bundled ComfyUI via the UI settings on first run.
    docker_image = "ghcr.io/michael-borck/puente-swarmui:latest"
    requires_gpu = True

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = dict(config.environment)

        fragment: dict[str, Any] = {
            "swarmui": {
                "image": self.docker_image,
                "build": {"context": "./dockerfiles/swarmui"},
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
