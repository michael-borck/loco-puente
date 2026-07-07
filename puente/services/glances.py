"""Glances — system + GPU monitoring web UI."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class GlancesService(ServiceBase):
    name = "glances"
    description = "System + GPU monitoring (CPU, RAM, disk, GPU, containers)"
    default_port = 61208
    install_method = "docker"
    docker_image = "nicolargo/glances:latest-full"
    requires_gpu = True  # for GPU stats; still runs (CPU/RAM only) without a GPU

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = {
            "GLANCES_OPT": "-w",  # -w = web server mode (port 61208)
            # Make nvidia-container-runtime inject libnvidia-ml (needed for GPU
            # stats). The deploy reservation alone doesn't reliably expose the
            # utility libs; these env vars do.
            "NVIDIA_VISIBLE_DEVICES": "all",
            "NVIDIA_DRIVER_CAPABILITIES": "utility",
        }
        env.update(config.environment)

        fragment: dict[str, Any] = {
            "glances": {
                "image": self.docker_image,
                "container_name": "puente-glances",
                "ports": [f"{port}:61208"],
                "environment": env,
                # host PID namespace -> see all host processes, not just the
                # container's; docker socket -> per-container stats.
                "pid": "host",
                "volumes": ["/var/run/docker.sock:/var/run/docker.sock:ro"],
                "restart": "unless-stopped",
            }
        }

        # GPU stats: request all GPUs (read-only monitoring, so all is fine).
        # Omitted gracefully if no GPU — Glances just shows CPU/RAM/disk.
        if config.gpu is not None or self.requires_gpu:
            fragment["glances"]["deploy"] = {
                "resources": {
                    "reservations": {
                        "devices": [
                            {
                                "driver": "nvidia",
                                "count": "all",
                                "capabilities": ["gpu", "utility"],
                            }
                        ]
                    }
                }
            }

        return fragment
