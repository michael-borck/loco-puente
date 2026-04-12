"""Abstract base class for all services."""

from __future__ import annotations

import socket
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from puente.models import ServiceConfig


@dataclass
class ServiceStatus:
    name: str
    running: bool
    port: int | None = None
    method: str = ""
    detail: str = ""


class ServiceBase(ABC):
    """Base class for all stack services."""

    name: str
    description: str
    default_port: int
    install_method: str  # "docker" | "native" | "external"
    docker_image: str | None = None
    requires_gpu: bool = False

    def is_port_active(self, port: int) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=2):
                return True
        except (ConnectionRefusedError, TimeoutError, OSError):
            return False

    @abstractmethod
    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        """Return docker-compose service dict, or None for non-Docker services."""
        ...

    def status(self, config: ServiceConfig) -> ServiceStatus:
        port = config.port or self.default_port
        running = self.is_port_active(port)
        return ServiceStatus(
            name=self.name,
            running=running,
            port=port,
            method=config.install_method,
            detail="responding" if running else "not responding",
        )

    def health_check(self, config: ServiceConfig) -> bool:
        port = config.port or self.default_port
        return self.is_port_active(port)

    def pre_start(self, config: ServiceConfig, data_dir: str) -> None:
        """Hook invoked before `docker compose up -d`. Override for config
        file pre-seeding, ownership fixes, etc. — anything that needs to be
        in place on disk before the container starts.
        """
        return None

    def post_start(self, config: ServiceConfig, data_dir: str) -> None:
        """Hook invoked after `docker compose up -d`. Override for model pulls, etc."""
        return None
