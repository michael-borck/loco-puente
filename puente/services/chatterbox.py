"""Chatterbox — voice-cloning TTS server (build from local checkout)."""

from __future__ import annotations

from typing import Any

from puente.models import ChatterboxConfig, ServiceConfig

from .base import ServiceBase


class ChatterboxService(ServiceBase):
    name = "chatterbox"
    description = "Voice-cloning TTS server (Chatterbox)"
    default_port = 8004
    install_method = "docker"
    docker_image = None  # built from the local checkout's Dockerfile
    requires_gpu = True

    # CUDA GOTCHA: Chatterbox's Dockerfile bases on nvidia/cuda:12.8.1-runtime.
    # The host NVIDIA driver/kernel must be new enough for CUDA 12.8 or the
    # container fails to see the GPU. Update the host driver first; the build
    # itself is straightforward but LONG (large ML deps). See docs/chatterbox-api.md.

    def compose_volumes(self, config: ServiceConfig) -> dict[str, dict[str, Any]]:
        return {"chatterbox-hf-cache": {}}

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        # external = point at an existing Chatterbox elsewhere; nothing runs here.
        if getattr(config, "install_method", "docker") == "external":
            return None

        port = config.port or self.default_port
        ctx = getattr(config, "build_context", "/home/michael/Chatterbox-TTS-Server")

        env = {
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "NVIDIA_DRIVER_CAPABILITIES": "compute,utility",
        }
        hf = getattr(config, "hf_token", None)
        if hf:
            env["HF_TOKEN"] = hf
        env.update(config.environment)

        fragment: dict[str, Any] = {
            "chatterbox": {
                "build": {
                    "context": ctx,
                    "dockerfile": "Dockerfile",
                    "args": ["RUNTIME=nvidia"],
                },
                "container_name": "puente-chatterbox",
                "ports": [f"{port}:8004"],
                # Bind-mount the checkout's data so existing voices / config /
                # reference audio are preserved and shared with the source repo.
                "volumes": [
                    f"{ctx}/config.yaml:/app/config.yaml",
                    f"{ctx}/voices:/app/voices",
                    f"{ctx}/reference_audio:/app/reference_audio",
                    f"{ctx}/outputs:/app/outputs",
                    f"{ctx}/logs:/app/logs",
                    "chatterbox-hf-cache:/app/hf_cache",
                ],
                "environment": env,
                "restart": "unless-stopped",
            }
        }

        # GPU request. Portable pattern:
        #   config.gpu is an int  -> pin to that specific device (this box: GPU 1,
        #                            keeping Chatterbox off the image-gen GPU 0).
        #   config.gpu is None    -> request ANY one GPU (count: 1), so a single-
        #                            GPU box still works instead of erroring on a
        #                            missing device id.
        # NOTE: pinning to device_ids:['1'] on a 1-GPU box is a HARD ERROR (no
        # fallback to GPU 0 or CPU), which is why None -> count:1 here.
        device: dict[str, Any] = {"driver": "nvidia", "capabilities": ["gpu"]}
        if config.gpu is not None:
            device["device_ids"] = [str(config.gpu)]
        else:
            device["count"] = 1
        fragment["chatterbox"]["deploy"] = {
            "resources": {"reservations": {"devices": [device]}}
        }

        return fragment
