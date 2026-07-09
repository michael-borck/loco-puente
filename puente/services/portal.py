"""Portal — static launcher page served by nginx."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class PortalService(ServiceBase):
    name = "portal"
    description = "Static service launcher page"
    default_port = 8080
    install_method = "docker"
    docker_image = "nginx:alpine"
    requires_gpu = False

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        fragment: dict[str, Any] = {
            "portal": {
                "image": self.docker_image,
                "container_name": "puente-portal",
                "ports": [f"{port}:80"],
                "volumes": [f"{data_dir}/portal:/usr/share/nginx/html:ro"],
                "restart": "unless-stopped",
            }
        }

        # GPU-stats sidecar: the portal is static nginx and can't run
        # nvidia-smi. This tiny CUDA-base container writes gpu-stats.json into
        # the portal html dir every few seconds; the page fetches + renders it.
        # Avoids the Glances-image NVML problem by using a proper CUDA base.
        #
        # Base is pinned to 12.4 (not 12.8) so this sidecar never becomes the
        # thing forcing a host-driver upgrade: 12.4 matches ComfyUI's cu124
        # wheels, the strictest real GPU service. The container only shells out
        # to nvidia-smi, so the base's CUDA version is otherwise irrelevant.
        fragment["portal-gpu-stats"] = {
            "image": "nvidia/cuda:12.4.1-base-ubuntu22.04",
            "container_name": "puente-portal-gpu-stats",
            "entrypoint": [
                "bash",
                "-c",
                # Loop: query nvidia-smi as CSV, wrap into JSON, write to the
                # shared html dir. 3s cadence is plenty for a glance.
                "while true; do "
                "nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu,temperature.gpu "
                "--format=csv,noheader,nounits 2>/dev/null "
                "| awk -F', *' 'BEGIN{print \"[\"} {if(NR>1)print \",\"; "
                "printf \"{\\\"index\\\":%s,\\\"name\\\":\\\"%s\\\",\\\"mem_used\\\":%s,\\\"mem_total\\\":%s,\\\"util\\\":%s,\\\"temp\\\":%s}\",$1,$2,$3,$4,$5,$6} "
                "END{print \"]\"}' > /html/gpu-stats.json.tmp && mv /html/gpu-stats.json.tmp /html/gpu-stats.json; "
                "sleep 3; done",
            ],
            "volumes": [f"{data_dir}/portal:/html"],
            "deploy": {
                "resources": {
                    "reservations": {
                        "devices": [
                            {"driver": "nvidia", "count": "all", "capabilities": ["gpu", "utility"]}
                        ]
                    }
                }
            },
            "environment": {
                "NVIDIA_VISIBLE_DEVICES": "all",
                "NVIDIA_DRIVER_CAPABILITIES": "utility",
            },
            "restart": "unless-stopped",
        }

        return fragment
