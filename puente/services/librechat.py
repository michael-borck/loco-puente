"""LibreChat — multi-provider chat UI (app + MongoDB)."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class LibreChatService(ServiceBase):
    name = "librechat"
    description = "Multi-provider chat UI (frontier-alternative front end)"
    default_port = 3080
    install_method = "docker"
    docker_image = "ghcr.io/danny-avila/librechat:latest"
    requires_gpu = False

    def compose_volumes(self, config: ServiceConfig) -> dict[str, dict[str, Any]]:
        return {"librechat-mongo": {}, "librechat-images": {}, "librechat-logs": {}}

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        # external = point LibreChat elsewhere; nothing runs here.
        if getattr(config, "install_method", "docker") == "external":
            return None

        port = config.port or self.default_port
        env = dict(config.environment)
        # Bundled mongo unless the config overrides it (e.g. external Atlas).
        mongo_uri = getattr(config, "mongo_uri", None) or "mongodb://librechat-mongo:27017/LibreChat"
        env.setdefault("MONGO_URI", mongo_uri)
        # Fits the mission: default the LLM backend at the local Ollama so
        # LibreChat works out-of-the-box against the free local model.
        env.setdefault("OPENAI_REVERSE_PROXY", "http://host.docker.internal:11434/v1")

        fragment: dict[str, Any] = {
            "librechat": {
                "image": self.docker_image,
                "container_name": "puente-librechat",
                "ports": [f"{port}:3080"],
                "environment": env,
                "extra_hosts": ["host.docker.internal:host-gateway"],
                "volumes": [
                    "librechat-images:/app/client/public/images",
                    "librechat-logs:/app/api/logs",
                ],
                "depends_on": ["librechat-mongo"],
                "restart": "unless-stopped",
            }
        }
        # Only run the bundled mongo when not using an external one.
        if not getattr(config, "mongo_uri", None):
            fragment["librechat-mongo"] = {
                "image": "mongo:7",
                "container_name": "puente-librechat-mongo",
                "command": "mongod --noauth",
                "volumes": ["librechat-mongo:/data/db"],
                "restart": "unless-stopped",
            }

        return fragment
