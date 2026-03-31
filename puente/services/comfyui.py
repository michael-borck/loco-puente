"""ComfyUI — local image generation (Docker with GPU)."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class ComfyUIService(ServiceBase):
    name = "comfyui"
    description = "Image generation (SD 1.5, SDXL, FLUX)"
    default_port = 8188
    install_method = "docker"
    docker_image = "mmartial/comfyui-nvidia-docker:ubuntu22_cuda12.4-latest"
    requires_gpu = True

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = {"USE_UV": "true"}
        env.update(config.environment)

        fragment: dict[str, Any] = {
            "comfyui": {
                "image": self.docker_image,
                "container_name": "puente-comfyui",
                "ports": [f"{port}:8188"],
                "volumes": [
                    f"{data_dir}/comfyui-run:/comfyui-run",
                    f"{data_dir}/comfyui-basedir:/comfyui-basedir",
                ],
                "environment": env,
                "restart": "unless-stopped",
            }
        }

        if config.gpu is not None:
            fragment["comfyui"]["deploy"] = {
                "resources": {
                    "reservations": {
                        "devices": [
                            {
                                "driver": "nvidia",
                                "device_ids": [str(config.gpu)],
                                "capabilities": ["gpu"],
                            }
                        ]
                    }
                }
            }

        return fragment
