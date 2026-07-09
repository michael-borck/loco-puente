"""Ollama — LLM inference. Either a native systemd install (managed: false) or
a puente-managed container (managed: true, install_method: docker)."""

from __future__ import annotations

import os
from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase

# Ollama's Linux installer creates a system user `ollama` with home
# /usr/share/ollama, so its store defaults to $HOME/.ollama. But .ollama/models
# is frequently a SYMLINK to a bigger disk — bind-mounting the parent would
# carry a symlink that dangles inside the container. So resolve to the real
# directory before mounting. Override by setting OLLAMA_MODELS_DIR under the
# service's `environment:` in puente.yml.
NATIVE_OLLAMA_HOME = "/usr/share/ollama/.ollama"


def _resolve_models_dir() -> str | None:
    """Real path of the native model store, or None if there isn't one.

    Note this probes the filesystem of whichever host generates the compose
    file. If you generate config on one machine and run it on another, set
    OLLAMA_MODELS_DIR explicitly rather than relying on autodetection.
    """
    models = os.path.join(NATIVE_OLLAMA_HOME, "models")
    if os.path.isdir(models):
        return os.path.realpath(models)
    return None


class OllamaService(ServiceBase):
    name = "ollama"
    description = "Local LLM inference (OpenAI-compatible API)"
    default_port = 11434
    # Default stays "native": most boxes already have ollama installed, and
    # puente's job is to coexist rather than take over. Set install_method:
    # docker + managed: true in puente.yml to have puente own it instead.
    install_method = "native"
    docker_image = "ollama/ollama:latest"
    requires_gpu = True

    def compose_volumes(self, config: ServiceConfig) -> dict[str, dict[str, Any]]:
        if config.install_method != "docker":
            return {}
        # A named volume is only needed when there is no existing store to adopt.
        if config.environment.get("OLLAMA_MODELS_DIR") or _resolve_models_dir():
            return {}
        return {"ollama-data": {}}

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        # compose.py already skips unmanaged / non-docker services, but be
        # explicit: a native systemd ollama has no compose representation.
        if config.install_method != "docker":
            return None

        # NOTE: OllamaConfig.instances (multi-instance, one per GPU) is only
        # honoured by the native path. The container path emits a single
        # instance on config.port / config.gpu.
        port = config.port or self.default_port

        env = {"OLLAMA_HOST": "0.0.0.0"}
        # OLLAMA_KEEP_ALIVE controls how long a model stays resident in VRAM
        # (default 5m). On a small card, shortening it trades load-tax for the
        # ability to share the GPU with image/voice services.
        env.update({k: v for k, v in config.environment.items() if k != "OLLAMA_MODELS_DIR"})

        # Adopt an existing native store rather than re-pulling tens of GB.
        # Mount it at /root/.ollama/models (NOT /root/.ollama) so we don't have
        # to also relocate the ollama identity keypair that lives alongside it.
        #
        # OWNERSHIP HAZARD, migration case only: the ollama/ollama image runs as
        # root, but a store created by the native installer is owned by the
        # `ollama` system user. Once the container pulls a model, the new blobs
        # are root-owned, and a later `systemctl start ollama` (running as
        # `ollama`) may not be able to read or evict them. A puente-only install
        # never hits this — the store is root-owned from the start.
        # To revert cleanly after a migration:
        #     sudo chown -R ollama:ollama <models_dir>
        models_dir = config.environment.get("OLLAMA_MODELS_DIR") or _resolve_models_dir()
        if models_dir:
            volumes = [f"{models_dir}:/root/.ollama/models"]
        else:
            volumes = ["ollama-data:/root/.ollama"]

        service: dict[str, Any] = {
            "image": self.docker_image,
            "container_name": "puente-ollama",
            # Publish on the host so both the reverse proxy and open-webui's
            # host.docker.internal:11434 keep resolving exactly as before.
            "ports": [f"{port}:11434"],
            "volumes": volumes,
            "environment": env,
            "restart": "unless-stopped",
        }

        if config.gpu is not None:
            service["deploy"] = {
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

        return {"ollama": service}
