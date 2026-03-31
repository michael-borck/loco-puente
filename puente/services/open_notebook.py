"""Open Notebook AI — research assistant and note-taking."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class OpenNotebookService(ServiceBase):
    name = "open_notebook"
    description = "Research assistant (PDF ingestion, notes, podcast generation)"
    default_port = 8502
    install_method = "docker"
    docker_image = "lfnovo/open_notebook:v1-latest-single"
    requires_gpu = False

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = {
            "SURREAL_URL": "ws://localhost:8000/rpc",
            "SURREAL_USER": "root",
            "SURREAL_PASSWORD": "root",
            "SURREAL_NAMESPACE": "open_notebook",
            "SURREAL_DATABASE": "open_notebook",
            "OPEN_NOTEBOOK_ENCRYPTION_KEY": "puente-notebook-secret-change-me",
        }
        env.update(config.environment)

        return {
            "open-notebook": {
                "image": self.docker_image,
                "container_name": "puente-open-notebook",
                "ports": [
                    f"{port}:8502",
                    "5055:5055",
                ],
                "volumes": [
                    f"{data_dir}/open-notebook:/app/data",
                    f"{data_dir}/open-notebook-db:/mydata",
                ],
                "environment": env,
                "extra_hosts": ["host.docker.internal:host-gateway"],
                "restart": "unless-stopped",
            }
        }
