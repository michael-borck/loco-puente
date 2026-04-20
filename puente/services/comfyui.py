"""ComfyUI — local image generation (Docker with GPU)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from puente.models import ComfyUIConfig, ServiceConfig

from .base import ServiceBase

# Written to {data_dir}/comfyui-run/user_script.bash which the mmartial image
# runs automatically before ComfyUI starts (as the comfy user, after venv creation).
_STARTUP_SCRIPT = """#!/bin/bash
# Puente ComfyUI setup — runs inside container before ComfyUI starts.

VENV_PIP="/comfy/mnt/venv/bin/pip"
MANAGER_REPO="https://github.com/ltdrdata/ComfyUI-Manager.git"
MANAGER_DIR="/basedir/custom_nodes/ComfyUI-Manager"

# Fix setuptools: versions >= 70 omit pkg_resources which many custom nodes need.
if [ -f "$VENV_PIP" ]; then
    "$VENV_PIP" install "setuptools<70" --quiet 2>&1 || true
fi

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
channel_url = default
preview_method = auto
badge_mode = none
git_exe =
update_interval = 600
enable_after_install = False
network_mode = public
security_level = weak
CONFIGEOF
fi

# Auto-install requirements for every custom node that has a requirements.txt.
# This ensures nodes installed via Manager (or manually) work after the next restart
# without needing manual "Try Fix" steps.
if [ -f "$VENV_PIP" ]; then
    for req in /basedir/custom_nodes/*/requirements.txt; do
        [ -f "$req" ] || continue
        node_name=$(basename "$(dirname "$req")")
        # Skip Manager itself — its deps are handled by ComfyUI's own install path.
        [ "$node_name" = "ComfyUI-Manager" ] && continue
        echo "[puente] Installing requirements for $node_name..."
        "$VENV_PIP" install -r "$req" --quiet 2>&1 || true
    done
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
        script = run_dir / "user_script.bash"
        script.write_text(_STARTUP_SCRIPT)
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
