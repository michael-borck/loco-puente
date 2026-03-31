"""Open WebUI — general AI chat interface."""

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
            # Ollama runs on the host, not in Docker
            "OLLAMA_BASE_URL": "http://host.docker.internal:11434",
            # Disable auth for PoC (network access controls who can reach it)
            "WEBUI_AUTH": "false",
            # SearXNG for web search in chat (container name on compose network)
            "RAG_WEB_SEARCH_ENGINE": "searxng",
            "SEARXNG_QUERY_URL": "http://puente-searxng:8080/search?q=<query>&format=json",
            # Speaches for voice (container name on compose network)
            "AUDIO_STT_ENGINE": "openai",
            "AUDIO_STT_OPENAI_API_BASE_URL": "http://puente-speaches:8000/v1",
            "AUDIO_STT_OPENAI_API_KEY": "not-needed",
            "AUDIO_TTS_ENGINE": "openai",
            "AUDIO_TTS_OPENAI_API_BASE_URL": "http://puente-speaches:8000/v1",
            "AUDIO_TTS_OPENAI_API_KEY": "not-needed",
            # ComfyUI for image generation (container name on compose network)
            "IMAGE_GENERATION_ENGINE": "comfyui",
            "COMFYUI_BASE_URL": "http://puente-comfyui:8188",
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
