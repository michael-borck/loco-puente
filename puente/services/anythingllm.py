"""AnythingLLM — unit-specific RAG chatbots."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class AnythingLLMService(ServiceBase):
    name = "anythingllm"
    description = "RAG chatbots (embeds in Blackboard, per-unit workspaces)"
    default_port = 3001
    install_method = "docker"
    docker_image = "mintplexlabs/anythingllm:latest"
    requires_gpu = False

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        # external = point at an existing AnythingLLM elsewhere; nothing runs here.
        if getattr(config, "install_method", "docker") == "external":
            return None

        port = config.port or self.default_port
        env = dict(config.environment)

        # Preserve the existing install's JWT_SECRET so embedded-chatbot embeds
        # and logged-in sessions survive the migration under Puente.
        jwt = getattr(config, "jwt_secret", None)
        if jwt:
            env.setdefault("JWT_SECRET", jwt)
        env.setdefault("STORAGE_DIR", "/app/server/storage")

        # storage_path lets Puente adopt an existing storage dir (workspaces,
        # embeddings, vector DB) in place instead of starting empty. Falls back
        # to Puente's own data dir for a fresh install.
        storage = getattr(config, "storage_path", None) or f"{data_dir}/anythingllm"

        return {
            "anythingllm": {
                "image": self.docker_image,
                "container_name": "puente-anythingllm",
                "ports": [f"{port}:3001"],
                "volumes": [f"{storage}:/app/server/storage"],
                "environment": env,
                "extra_hosts": ["host.docker.internal:host-gateway"],
                "restart": "unless-stopped",
            }
        }
