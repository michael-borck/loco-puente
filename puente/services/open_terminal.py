"""Open Terminal — code execution sandbox for Open WebUI."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class OpenTerminalService(ServiceBase):
    name = "open_terminal"
    description = "Code execution sandbox (Python, PDF/DOCX generation)"
    default_port = 8100
    install_method = "docker"
    docker_image = "ghcr.io/open-webui/open-terminal:latest"
    requires_gpu = False

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = {
            "OPEN_TERMINAL_API_KEY": "puente-terminal-key",
        }
        env.update(config.environment)

        return {
            "open-terminal": {
                "image": self.docker_image,
                "container_name": "puente-open-terminal",
                "ports": [f"{port}:8000"],
                "volumes": [f"{data_dir}/open-terminal:/home/user"],
                "environment": env,
                "restart": "unless-stopped",
            }
        }
