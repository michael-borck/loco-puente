"""Speaches — local TTS/STT (OpenAI Audio API compatible)."""

from __future__ import annotations

import time
import urllib.error
import urllib.request
from typing import Any

from rich.console import Console

from puente.models import ServiceConfig, SpeachesConfig

from .base import ServiceBase

console = Console()


class SpeachesService(ServiceBase):
    name = "speaches"
    description = "Voice: speech-to-text (Whisper) and text-to-speech (Kokoro)"
    default_port = 8000
    install_method = "docker"
    docker_image = "ghcr.io/speaches-ai/speaches:latest-cuda-12.4.1"
    requires_gpu = True

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = dict(config.environment)

        fragment: dict[str, Any] = {
            "speaches": {
                "image": self.docker_image,
                "container_name": "puente-speaches",
                "ports": [f"{port}:8000"],
                "volumes": [f"{data_dir}/speaches:/root/.cache"],
                "environment": env,
                "restart": "unless-stopped",
            }
        }

        if config.gpu is not None:
            fragment["speaches"]["deploy"] = {
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

    def post_start(self, config: ServiceConfig, data_dir: str) -> None:
        if not isinstance(config, SpeachesConfig) or not config.models:
            return

        port = config.port or self.default_port
        base_url = f"http://127.0.0.1:{port}"

        if not self._wait_for_ready(base_url, timeout=120):
            console.print(
                f"[yellow]Speaches did not become ready on {base_url}; skipping model pre-pull.[/yellow]"
            )
            return

        # Always POST each configured model. Speaches' /v1/models endpoint
        # reflects its in-memory registry, which is empty after every container
        # restart even though the cached files persist via the volume mount.
        # POSTing is idempotent: instant if cached, downloads if not. Skipping
        # based on /v1/models leaves the registry empty after restart, which
        # surfaces in clients (Open WebUI, etc.) as "model not found" errors.
        for model_id in config.models:
            console.print(f"  [cyan]Registering Speaches model:[/cyan] {model_id}")
            try:
                req = urllib.request.Request(
                    f"{base_url}/v1/models/{model_id}", method="POST"
                )
                with urllib.request.urlopen(req, timeout=1800) as resp:
                    resp.read()
                console.print(f"  [green]Ready:[/green] {model_id}")
            except urllib.error.HTTPError as e:
                console.print(f"  [red]Failed ({e.code}):[/red] {model_id} — {e.reason}")
            except Exception as e:  # noqa: BLE001
                console.print(f"  [red]Failed:[/red] {model_id} — {e}")

    def _wait_for_ready(self, base_url: str, timeout: int = 120) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                with urllib.request.urlopen(f"{base_url}/v1/models", timeout=5) as resp:
                    if resp.status == 200:
                        return True
            except Exception:
                pass
            time.sleep(2)
        return False
