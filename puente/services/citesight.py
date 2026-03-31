"""CiteSight — citation verification and writing quality checker."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class CiteSightService(ServiceBase):
    name = "citesight"
    description = "Citation verification and writing quality checker"
    default_port = 3010
    install_method = "docker"
    docker_image = "michaelborck/cite-sight:latest"
    requires_gpu = False

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = {
            "REDIS_URL": "redis://puente-citesight-redis:6379",
            "PORT": "3000",
        }
        env.update(config.environment)

        return {
            "citesight": {
                "image": self.docker_image,
                "container_name": "puente-citesight",
                "ports": [f"{port}:3000"],
                "environment": env,
                "depends_on": ["citesight-redis"],
                "restart": "unless-stopped",
            },
            "citesight-redis": {
                "image": "redis:7-alpine",
                "container_name": "puente-citesight-redis",
                "restart": "unless-stopped",
            },
        }
