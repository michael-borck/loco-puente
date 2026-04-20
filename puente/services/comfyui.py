"""ComfyUI — local image generation (Docker with GPU)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from puente.models import ComfyUIConfig, ServiceConfig

from .base import ServiceBase

# Written to {data_dir}/comfyui-run/user_script.bash — runs before the mmartial
# upgrade loop (early startup hook: clone Manager, write config).
_STARTUP_SCRIPT = """#!/bin/bash
# Puente ComfyUI early setup — clones Manager before ComfyUI starts.

MANAGER_REPO="https://github.com/ltdrdata/ComfyUI-Manager.git"
MANAGER_DIR="/basedir/custom_nodes/ComfyUI-Manager"

# Clone or update ComfyUI-Manager.
mkdir -p /basedir/custom_nodes
if [ ! -d "$MANAGER_DIR" ]; then
    git clone --depth 1 "$MANAGER_REPO" "$MANAGER_DIR" 2>&1 || true
else
    git -C "$MANAGER_DIR" pull --quiet 2>&1 || true
fi

# Write Manager config (always overwrite to keep settings correct).
if [ -d "$MANAGER_DIR" ]; then
    cat > "$MANAGER_DIR/config.ini" << 'CONFIGEOF'
[default]
channel_url = local
preview_method = auto
badge_mode = none
git_exe =
update_interval = 600
enable_after_install = False
network_mode = public
security_level = weak
CONFIGEOF
fi
"""

# Written to {data_dir}/comfyui-run/postvenv_script.bash — runs AFTER the mmartial
# upgrade loop (so our setuptools pin isn't overwritten) but before torch/ComfyUI.
_POSTVENV_SCRIPT = """#!/bin/bash
# Puente ComfyUI post-upgrade setup — runs after mmartial's package upgrade loop.

VENV_PIP="/comfy/mnt/venv/bin/pip"

# Pin setuptools<70: mmartial upgrades to 82.x which omits pkg_resources from
# uv venvs. Many custom nodes import pkg_resources at load time.
# NOTE: do NOT install custom node requirements here — this hook runs before torch,
# so compiled extensions (scikit-image, opencv, etc.) would be built against the
# wrong numpy ABI. Use ComfyUI-Manager's "Try Fix" button for nodes with compiled deps.
if [ -f "$VENV_PIP" ]; then
    "$VENV_PIP" install "setuptools<70" --quiet 2>&1 || true
fi
"""


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
        run_dir = Path(data_dir) / "comfyui-run"
        run_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in [
            ("user_script.bash", _STARTUP_SCRIPT),
            ("postvenv_script.bash", _POSTVENV_SCRIPT),
        ]:
            script = run_dir / filename
            script.write_text(content)
            script.chmod(0o755)

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
                "init": True,
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
