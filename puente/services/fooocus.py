"""Fooocus — opinionated SDXL image-gen UI (Docker, GPU)."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class FooocusService(ServiceBase):
    name = "fooocus"
    description = "Opinionated SDXL UI with auto-enhancement"
    default_port = 7865
    install_method = "docker"
    # Built locally from puente/dockerfiles/fooocus — lllyasviel ships
    # installer scripts but no Docker image. The volume layout below
    # mirrors what Fooocus expects internally so model downloads persist
    # across restarts.
    docker_image = None
    requires_gpu = True

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = dict(config.environment)

        fragment: dict[str, Any] = {
            "fooocus": {
                "build": {"context": "./dockerfiles/fooocus"},
                "image": "puente-fooocus:local",
                "container_name": "puente-fooocus",
                "ports": [f"{port}:7865"],
                "volumes": [
                    f"{data_dir}/fooocus/models:/content/Fooocus/models",
                    f"{data_dir}/fooocus/outputs:/content/Fooocus/outputs",
                ],
                "environment": env,
                "restart": "unless-stopped",
            }
        }

        if config.gpu is not None:
            fragment["fooocus"]["deploy"] = {
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
