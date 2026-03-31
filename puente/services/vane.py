"""Vane (formerly Perplexica) — cited AI-powered web search."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class VaneService(ServiceBase):
    name = "vane"
    description = "Cited AI web search (Perplexity-style, formerly Perplexica)"
    default_port = 3005
    install_method = "docker"
    docker_image = "itzcrazykns1337/vane:slim-latest"
    requires_gpu = False

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = {
            "SEARXNG_API_URL": "http://puente-searxng:8080",
        }
        env.update(config.environment)

        return {
            "vane": {
                "image": self.docker_image,
                "container_name": "puente-vane",
                "ports": [f"{port}:3000"],
                "volumes": [f"{data_dir}/vane:/home/vane/data"],
                "environment": env,
                "extra_hosts": ["host.docker.internal:host-gateway"],
                "depends_on": ["searxng"],
                "restart": "unless-stopped",
            }
        }
