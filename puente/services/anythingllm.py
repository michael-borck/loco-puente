"""AnythingLLM — unit-specific RAG chatbots."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class AnythingLLMService(ServiceBase):
    name = "anythingllm"
    description = "RAG chatbots (embeds in Blackboard, per-unit workspaces)"
    default_port = 3002
    install_method = "docker"
    docker_image = "mintplexlabs/anythingllm:latest"
    requires_gpu = False

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = dict(config.environment)

        return {
            "anythingllm": {
                "image": self.docker_image,
                "container_name": "puente-anythingllm",
                "ports": [f"{port}:3001"],
                "volumes": [f"{data_dir}/anythingllm:/app/server/storage"],
                "environment": env,
                "extra_hosts": ["host.docker.internal:host-gateway"],
                "restart": "unless-stopped",
            }
        }
