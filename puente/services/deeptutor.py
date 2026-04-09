"""DeepTutor — agent-native personalised learning assistant."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class DeepTutorService(ServiceBase):
    name = "deeptutor"
    description = "Personalised learning assistant (RAG, quizzes, deep solve, research)"
    default_port = 3782
    install_method = "docker"
    docker_image = "ghcr.io/hkuds/deeptutor:latest"
    requires_gpu = False

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = {
            "LLM_BINDING": "ollama",
            "LLM_MODEL": "llama3.1:8b-q4_k_m",
            "LLM_HOST": "http://host.docker.internal:11434/v1",
            "LLM_API_KEY": "not-needed",
            "EMBEDDING_BINDING": "ollama",
            "EMBEDDING_MODEL": "nomic-embed-text",
            "EMBEDDING_HOST": "http://host.docker.internal:11434/v1",
            "EMBEDDING_API_KEY": "not-needed",
            "SEARXNG_URL": "http://host.docker.internal:8888",
        }
        env.update(config.environment)

        return {
            "deeptutor": {
                "image": self.docker_image,
                "container_name": "puente-deeptutor",
                "ports": [f"{port}:3782"],
                "volumes": [
                    f"{data_dir}/deeptutor/user:/app/data/user",
                    f"{data_dir}/deeptutor/knowledge_bases:/app/data/knowledge_bases",
                ],
                "environment": env,
                "extra_hosts": ["host.docker.internal:host-gateway"],
                "restart": "unless-stopped",
            }
        }
