"""Voicebox — local voice cloning / TTS studio (under evaluation)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class VoiceboxService(ServiceBase):
    name = "voicebox"
    description = "Local voice cloning + TTS studio (ElevenLabs alternative)"
    default_port = 17493
    install_method = "docker"
    # Upstream ships a multi-stage Dockerfile that copies from its own repo
    # layout, so we let Compose build directly from the upstream git context
    # rather than maintaining a parallel Dockerfile under dockerfiles/.
    docker_image = None
    requires_gpu = False

    def pre_start(self, config: ServiceConfig, data_dir: str) -> None:
        # Voicebox runs as a non-root `voicebox` system user inside the
        # container (rare among puente services). The container's UID won't
        # match the host's, so bind-mounted directories created by puente
        # are unwritable from inside — the SQLite DB init then fails with
        # "unable to open database file" and uvicorn exits. Pre-creating the
        # dirs world-writable lets the in-container user open them.
        for sub in ("output", "data", "hf-cache"):
            d = Path(data_dir) / "voicebox" / sub
            d.mkdir(parents=True, exist_ok=True)
            os.chmod(d, 0o777)

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = {"LOG_LEVEL": "info", "NUMBA_CACHE_DIR": "/tmp/numba_cache"}
        env.update(config.environment)

        return {
            "voicebox": {
                "build": {"context": "https://github.com/jamiepine/voicebox.git"},
                "container_name": "puente-voicebox",
                "ports": [f"{port}:17493"],
                "volumes": [
                    f"{data_dir}/voicebox/output:/app/data/generations",
                    f"{data_dir}/voicebox/data:/app/data",
                    f"{data_dir}/voicebox/hf-cache:/home/voicebox/.cache/huggingface",
                ],
                "environment": env,
                "restart": "unless-stopped",
            }
        }
