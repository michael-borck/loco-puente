"""Open WebUI — general student AI chat interface."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class OpenWebUIService(ServiceBase):
    name = "open_webui"
    description = "AI chat interface (voice, images, web search)"
    default_port = 3000
    install_method = "docker"
    docker_image = "ghcr.io/open-webui/open-webui:main"
    requires_gpu = False

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = {
            "OLLAMA_BASE_URL": "http://host.docker.internal:11434",
            "WEBUI_AUTH": "false",
        }
        env.update(config.environment)

        return {
            "open-webui": {
                "image": self.docker_image,
                "container_name": "puente-open-webui",
                "ports": [f"{port}:8080"],
                "volumes": [f"{data_dir}/open-webui:/app/backend/data"],
                "environment": env,
                "extra_hosts": ["host.docker.internal:host-gateway"],
                "restart": "unless-stopped",
            }
        }
