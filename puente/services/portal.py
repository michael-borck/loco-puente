"""Portal — static launcher page served by nginx."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class PortalService(ServiceBase):
    name = "portal"
    description = "Static service launcher page"
    default_port = 8080
    install_method = "docker"
    docker_image = "nginx:alpine"
    requires_gpu = False

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        return {
            "portal": {
                "image": self.docker_image,
                "container_name": "puente-portal",
                "ports": [f"{port}:80"],
                "volumes": [f"{data_dir}/portal:/usr/share/nginx/html:ro"],
                "restart": "unless-stopped",
            }
        }
