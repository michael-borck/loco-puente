"""Uptime Kuma — service uptime monitoring + alerting."""

from __future__ import annotations

from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class UptimeKumaService(ServiceBase):
    name = "uptime_kuma"
    description = "Uptime monitoring + alerts (ping/HTTP checks, status page)"
    default_port = 3002  # host port; 3001 is AnythingLLM's default, so remap
    install_method = "docker"
    docker_image = "louislam/uptime-kuma:1"
    requires_gpu = False

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        return {
            "uptime-kuma": {
                "image": self.docker_image,
                "container_name": "puente-uptime-kuma",
                "ports": [f"{port}:3001"],
                "environment": dict(config.environment),
                "volumes": [f"{data_dir}/uptime-kuma:/app/data"],
                # Lets monitors reach host-level services (native Ollama on
                # :11434, portal, glances) as http://host.docker.internal:PORT
                # as well as stack services by compose service name.
                "extra_hosts": ["host.docker.internal:host-gateway"],
                "restart": "unless-stopped",
            }
        }
