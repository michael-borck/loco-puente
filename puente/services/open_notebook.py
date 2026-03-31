"""Open Notebook AI — research assistant and note-taking."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class OpenNotebookService(ServiceBase):
    name = "open_notebook"
    description = "Research assistant (PDF ingestion, notes, podcast generation)"
    default_port = 8080
    install_method = "docker"
    docker_image = "lfnovo/open_notebook:v1-latest-single"
    requires_gpu = False

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = dict(config.environment)

        return {
            "open-notebook": {
                "image": self.docker_image,
                "container_name": "puente-open-notebook",
                "ports": [f"{port}:8080"],
                "volumes": [f"{data_dir}/open-notebook:/app/data"],
                "environment": env,
                "extra_hosts": ["host.docker.internal:host-gateway"],
                "restart": "unless-stopped",
            }
        }
