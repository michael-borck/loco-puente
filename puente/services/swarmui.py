"""SwarmUI — friendly image-gen front-end that uses ComfyUI as the backend."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rich.console import Console

from puente.models import ServiceConfig

from .base import ServiceBase

console = Console()


# FDS (Frenetic Data Syntax) config telling SwarmUI to use a single
# external ComfyUI backend pointed at the puente-comfyui container.
# Format derived from SwarmUI's own BackendHandler.cs save logic and the
# ComfyUIAPISettings C# class. The "comfyui_api" type is the registered
# ID for the "ComfyUI API By URL" backend; without this file SwarmUI
# defaults to spinning up its own bundled ComfyUI instance and downloads
# multi-GB of duplicate models.
BACKENDS_FDS_CONTENT = """\
0:
    type: comfyui_api
    title: External ComfyUI (puente-comfyui)
    enabled: true
    settings:
        Address: http://puente-comfyui:8188
        AllowIdle: false
        OverQueue: 1
        EnableFrontendDev: false
"""


class SwarmUIService(ServiceBase):
    name = "swarmui"
    description = "Friendly image generation UI (uses ComfyUI backend)"
    default_port = 7801
    install_method = "docker"
    # Pull-first, build-fallback. Built and pushed to GHCR by the
    # .github/workflows/build-images.yml workflow. Configure SwarmUI to
    # talk to the existing puente-comfyui container instead of spinning
    # up its own bundled ComfyUI via the UI settings on first run.
    docker_image = "ghcr.io/michael-borck/puente-swarmui:latest"
    requires_gpu = True

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = dict(config.environment)

        fragment: dict[str, Any] = {
            "swarmui": {
                "image": self.docker_image,
                "build": {"context": "./dockerfiles/swarmui"},
                "container_name": "puente-swarmui",
                "ports": [f"{port}:7801"],
                "volumes": [
                    f"{data_dir}/swarmui:/SwarmUI/Data",
                ],
                "environment": env,
                "restart": "unless-stopped",
            }
        }

        if config.gpu is not None:
            fragment["swarmui"]["deploy"] = {
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

    def pre_start(self, config: ServiceConfig, data_dir: str) -> None:
        """Pre-seed Backends.fds so SwarmUI uses puente-comfyui instead of
        downloading its own bundled ComfyUI on first launch. Idempotent —
        only writes the file if it doesn't already exist, so any user
        customisation via the SwarmUI UI is preserved across restarts.
        """
        backends_file = Path(data_dir) / "swarmui" / "Backends.fds"
        if backends_file.exists():
            return
        backends_file.parent.mkdir(parents=True, exist_ok=True)
        backends_file.write_text(BACKENDS_FDS_CONTENT)
        console.print(
            f"  [cyan]Pre-seeded SwarmUI external ComfyUI backend:[/cyan] {backends_file}"
        )
