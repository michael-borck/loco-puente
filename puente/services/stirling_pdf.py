"""Stirling PDF — self-hosted PDF toolkit."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class StirlingPDFService(ServiceBase):
    name = "stirling_pdf"
    description = "PDF tools (merge, split, OCR, convert)"
    default_port = 8089
    install_method = "docker"
    docker_image = "frooodle/s-pdf:latest"
    requires_gpu = False

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        return {
            "stirling-pdf": {
                "image": self.docker_image,
                "container_name": "puente-stirling-pdf",
                "ports": [f"{port}:8080"],
                "environment": dict(config.environment),
                "restart": "unless-stopped",
            }
        }
