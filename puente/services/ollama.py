"""Ollama — native systemd install."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class OllamaService(ServiceBase):
    name = "ollama"
    description = "Local LLM inference (OpenAI-compatible API)"
    default_port = 11434
    install_method = "native"
    docker_image = None
    requires_gpu = True

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        return None  # Ollama runs as systemd, not Docker
