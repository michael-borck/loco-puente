"""Excalidraw — collaborative whiteboard."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class ExcalidrawService(ServiceBase):
    name = "excalidraw"
    description = "Collaborative whiteboard and diagramming"
    default_port = 3333
    install_method = "docker"
    docker_image = "excalidraw/excalidraw:latest"
    requires_gpu = False

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        return {
            "excalidraw": {
                "image": self.docker_image,
                "container_name": "puente-excalidraw",
                "ports": [f"{port}:80"],
                "environment": dict(config.environment),
                "restart": "unless-stopped",
            }
        }
