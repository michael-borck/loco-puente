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
    #: True when `docker_image` is a reference in puente's own GHCR namespace,
    #: published by .github/workflows/build-images.yml. Those images are
    #: linux/amd64 only (see the workflow's `platforms:`), which every current
    #: target is — but an arm64 host (e.g. an M3 Ultra) cannot run them, and
    #: `puente doctor` says so rather than letting the pull fail obscurely.
    puente_published: bool = False

    def gpu_reservation(self, gpu: str | int | None) -> dict[str, Any] | None:
        """Compose `deploy` block pinning this service to one GPU, or None.

        Centralised so every GPU service pins identically. Accepts a UUID or a
        legacy integer index; see ServiceConfig.gpu.

        Returns None when nothing is pinned, which emits NO deploy block at all.
        Note that is not "no GPU" — with the nvidia runtime as Docker's default,
        an unpinned container sees every card.
        """
        if gpu is None:
            return None
        return {
            "resources": {
                "reservations": {
                    "devices": [
                        {
                            "driver": "nvidia",
                            "device_ids": [str(gpu)],
                            "capabilities": ["gpu"],
                        }
                    ]
                }
            }
        }

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

    def compose_volumes(self, config: ServiceConfig) -> dict[str, dict[str, Any]]:
        """Return top-level named-volume declarations this service requires.

        Compose requires named volumes referenced by services to be declared
        at the file's top level. Most puente services use bind mounts and
        return nothing here. Services that need Docker-managed volumes (e.g.
        because they run as a non-root user inside the container) should
        return a dict like ``{"voicebox-data": {}}``.
        """
        return {}

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
