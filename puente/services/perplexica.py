"""Perplexica — cited AI-powered web search."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class PerplexicaService(ServiceBase):
    name = "perplexica"
    description = "Cited AI web search (Perplexity-style)"
    default_port = 3001
    install_method = "docker"
    docker_image = "ghcr.io/itzcrazykns/perplexica:latest"
    requires_gpu = False

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = dict(config.environment)

        return {
            "perplexica": {
                "image": self.docker_image,
                "container_name": "puente-perplexica",
                "ports": [f"{port}:3001"],
                "volumes": [f"{data_dir}/perplexica:/app/data"],
                "environment": env,
                "extra_hosts": ["host.docker.internal:host-gateway"],
                "restart": "unless-stopped",
            }
        }
