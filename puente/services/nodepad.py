"""Nodepad — visual node-based note-taking (Next.js, localStorage)."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class NodepadService(ServiceBase):
    name = "nodepad"
    description = "Visual node-based note-taking and knowledge graph"
    default_port = 3004
    install_method = "docker"
    docker_image = "ghcr.io/michael-borck/puente-nodepad:latest"
    requires_gpu = False

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        return {
            "nodepad": {
                "image": self.docker_image,
                "build": {"context": "./dockerfiles/nodepad"},
                "container_name": "puente-nodepad",
                "ports": [f"{port}:3000"],
                "environment": dict(config.environment),
                "restart": "unless-stopped",
            }
        }
