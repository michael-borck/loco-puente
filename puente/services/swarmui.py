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
    # Built locally from puente/dockerfiles/swarmui — SwarmUI ships installer
    # scripts but no Docker image. We build from source against the official
    # mcr.microsoft.com/dotnet/sdk:8.0 base. Configure to talk to the
    # existing puente-comfyui container instead of spinning up its own
    # bundled ComfyUI (set via the Data/Settings.fds file on first run, or
    # via UI settings).
    docker_image = None
    requires_gpu = True

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = dict(config.environment)

        fragment: dict[str, Any] = {
            "swarmui": {
                "build": {"context": "./dockerfiles/swarmui"},
                "image": "puente-swarmui:local",
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
