"""SearXNG — private web search backend."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class SearXNGService(ServiceBase):
    name = "searxng"
    description = "Private web search (serves Open WebUI and Perplexica)"
    default_port = 8888
    install_method = "docker"
    docker_image = "searxng/searxng:latest"
    requires_gpu = False

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = {
            "SEARXNG_BASE_URL": f"http://localhost:{port}",
        }
        env.update(config.environment)

        return {
            "searxng": {
                "image": self.docker_image,
                "container_name": "puente-searxng",
                "ports": [f"{port}:8080"],
                "volumes": [f"{data_dir}/searxng:/etc/searxng"],
                "environment": env,
                "restart": "unless-stopped",
            }
        }
