"""ComfyUI — local image generation (Docker with GPU)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from puente.models import ComfyUIConfig, ServiceConfig

from .base import ServiceBase

_MANAGER_REPO = "https://github.com/ltdrdata/ComfyUI-Manager.git"
_MANAGER_DIR = "ComfyUI-Manager"
_MANAGER_CONFIG = """\
[default]
channel_url = default
preview_method = auto
badge_mode = none
git_exe =
update_interval = 600
enable_after_install = False
network_mode = public
security_level = weak
"""


def _write_manager_config(manager_path: Path) -> None:
    (manager_path / "config.ini").write_text(_MANAGER_CONFIG)


class ComfyUIService(ServiceBase):
    name = "comfyui"
    description = "Image generation (SD 1.5, SDXL, FLUX)"
    default_port = 8188
    install_method = "docker"
    docker_image = "ghcr.io/michael-borck/puente-comfyui:latest"
    requires_gpu = True

    def pre_start(self, config: ServiceConfig, data_dir: str) -> None:
        if not isinstance(config, ComfyUIConfig) or not config.install_manager:
            return
        custom_nodes = Path(data_dir) / "comfyui-basedir" / "custom_nodes"
        custom_nodes.mkdir(parents=True, exist_ok=True)
        manager_path = custom_nodes / _MANAGER_DIR
        if not manager_path.exists():
            subprocess.run(
                ["git", "clone", "--depth", "1", _MANAGER_REPO, str(manager_path)],
                check=True,
            )
        else:
            subprocess.run(["git", "-C", str(manager_path), "pull"], check=True)
        _write_manager_config(manager_path)

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = {
            "USE_UV": "true",
            "WANTED_UID": "1000",
            "WANTED_GID": "1000",
            "BASE_DIRECTORY": "/basedir",
            "SECURITY_LEVEL": "weak",
        }
        env.update(config.environment)

        fragment: dict[str, Any] = {
            "comfyui": {
                "image": self.docker_image,
                "build": {"context": "./dockerfiles/comfyui"},
                "container_name": "puente-comfyui",
                "ports": [f"{port}:8188"],
                "volumes": [
                    f"{data_dir}/comfyui-run:/comfy/mnt",
                    f"{data_dir}/comfyui-basedir:/basedir",
                    f"{data_dir}/comfyui-basedir/custom_nodes:/comfy/ComfyUI/custom_nodes",
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
