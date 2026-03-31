"""JupyterLab — browser-based Python notebook."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class JupyterService(ServiceBase):
    name = "jupyter"
    description = "Browser-based Python notebook (JupyterLab)"
    default_port = 8888
    install_method = "docker"
    docker_image = "jupyter/minimal-notebook:latest"
    requires_gpu = False

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = {
            "JUPYTER_TOKEN": "",
        }
        env.update(config.environment)

        return {
            "jupyter": {
                "image": self.docker_image,
                "container_name": "puente-jupyter",
                "ports": [f"{port}:8888"],
                "volumes": [f"{data_dir}/jupyter-notebooks:/home/jovyan/work"],
                "environment": env,
                "restart": "unless-stopped",
            }
        }
