"""Detect existing service installations."""

from __future__ import annotations

import shutil
import socket
import subprocess
from dataclasses import dataclass
from typing import Literal


@dataclass
class ExistingInstall:
    service: str
    method: Literal["systemd", "docker", "process", "port"]
    detail: str
    port: int | None = None


def check_port(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is in use."""
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False


def check_systemd(service_name: str) -> bool:
    """Check if a systemd service is active."""
    try:
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip() == "active"
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_docker_container(name_pattern: str) -> str | None:
    """Check for a running Docker container matching a name pattern.

    Returns the container name if found, None otherwise.
    """
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={name_pattern}", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        names = result.stdout.strip()
        return names.splitlines()[0] if names else None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def check_binary(name: str) -> bool:
    """Check if a binary is on PATH."""
    return shutil.which(name) is not None


def detect_all() -> list[ExistingInstall]:
    """Scan for all known service installations."""
    found: list[ExistingInstall] = []

    # Ollama
    if check_systemd("ollama"):
        found.append(ExistingInstall("ollama", "systemd", "ollama.service active", 11434))
    elif check_binary("ollama"):
        found.append(ExistingInstall("ollama", "process", "ollama binary on PATH"))
    if check_port(11434):
        if not any(f.service == "ollama" for f in found):
            found.append(ExistingInstall("ollama", "port", "port 11434 in use", 11434))

    # Docker-based services
    docker_services = {
        "open-webui": ("open-webui", 3000),
        "vane": ("vane", 3005),
        "anythingllm": ("anythingllm", 3001),
        "speaches": ("speaches", 8000),
        "open-notebook": ("open-notebook", 8080),
        "stirling-pdf": ("stirling", 8089),
        "searxng": ("searxng", 8888),
        "excalidraw": ("excalidraw", 3333),
    }

    for service, (pattern, port) in docker_services.items():
        container = check_docker_container(pattern)
        if container:
            found.append(
                ExistingInstall(service, "docker", f"container: {container}", port)
            )
        elif check_port(port):
            found.append(
                ExistingInstall(service, "port", f"port {port} in use", port)
            )

    # ComfyUI
    if check_port(8188):
        found.append(ExistingInstall("comfyui", "port", "port 8188 in use", 8188))

    return found
