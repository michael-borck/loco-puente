"""ComfyUI — local image generation (native venv install)."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class ComfyUIService(ServiceBase):
    name = "comfyui"
    description = "Image generation (SD 1.5, SDXL, FLUX)"
    default_port = 8188
    install_method = "native"
    docker_image = None
    requires_gpu = True

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        return None  # ComfyUI runs as native venv, not Docker
