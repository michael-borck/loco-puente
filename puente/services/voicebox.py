"""Voicebox — local voice cloning / TTS studio (under evaluation)."""

from __future__ import annotations

import subprocess
from typing import Any

from rich.console import Console

from puente.models import ServiceConfig, VoiceboxConfig

from .base import ServiceBase

console = Console()

UPSTREAM_REPO = "jamiepine/voicebox"


class VoiceboxService(ServiceBase):
    name = "voicebox"
    description = "Local voice cloning + TTS studio (ElevenLabs alternative)"
    default_port = 17493
    install_method = "docker"
    # Upstream ships a multi-stage Dockerfile that copies from its own repo
    # layout, so we let Compose build directly from the upstream git context
    # rather than maintaining a parallel Dockerfile under dockerfiles/.
    docker_image = None
    # Runs fine on CPU, but its bundled torch is a cu130 build and will use a
    # GPU if one is handed to it — no extra CUDA libs needed (voicebox's own
    # /backend/download-cuda is unnecessary). Set `gpu:` in puente.yml to pin
    # it to a card. cu130 wheels need host driver >= 580.
    requires_gpu = False

    # Voicebox is the only puente service that runs as a non-root user inside
    # the container (USER voicebox in upstream's Dockerfile). Bind mounts
    # would require world-writable host dirs to be usable from inside; named
    # Docker volumes sidestep that — Docker manages permissions and the
    # in-container voicebox user owns its own data.
    #
    # We use a single named volume mounted at /app/data because that path is
    # explicitly created and chown'd to voicebox:voicebox in the upstream
    # Dockerfile. HF cache is redirected (via HF_HOME) into a subdirectory
    # of that volume so it inherits the same correct permissions, instead of
    # mounting a second volume at /home/voicebox/.cache/huggingface where the
    # path doesn't exist in the image and Docker creates it as root.
    #
    # To grab generated audio off the host:
    #   docker cp puente-voicebox:/app/data/generations ./voicebox-output

    def compose_volumes(self, config: ServiceConfig) -> dict[str, dict[str, Any]]:
        return {"voicebox-data": {}}

    @staticmethod
    def _build_context(config: ServiceConfig) -> str:
        """Compose git build context, honouring an optional owner/repo@ref override."""
        build_ref = getattr(config, "build_ref", None) or UPSTREAM_REPO
        repo, _, ref = build_ref.partition("@")
        context = f"https://github.com/{repo}.git"
        # Compose selects a branch/tag/commit with a '#fragment' on the git URL.
        return f"{context}#{ref}" if ref else context

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = {
            "LOG_LEVEL": "info",
            "NUMBA_CACHE_DIR": "/tmp/numba_cache",
            "HF_HOME": "/app/data/hf-cache",
        }

        # Unload idle models so a dormant voicebox stops pinning the card. Stock
        # upstream has no idle unloading (jamiepine/voicebox#889), so only set
        # this when building from a fork that can actually honour it -- otherwise
        # it is a knob that looks live and silently does nothing.
        if getattr(config, "build_ref", None):
            env["VOICEBOX_IDLE_UNLOAD_SECONDS"] = "600"

        env.update(config.environment)

        service: dict[str, Any] = {
            "container_name": "puente-voicebox",
            "ports": [f"{port}:17493"],
            "volumes": ["voicebox-data:/app/data"],
            "environment": env,
            # unless-stopped, but with backoff: voicebox and ollama share the
            # 16GB card this service is pinned to, and at boot both try to load
            # at once. Observed 2026-10-10: voicebox lost with
            # `cudaErrorDevicesUnavailable`, served /health 200, then exited —
            # and plain `unless-stopped` restarted it so fast that the container
            # logged a shutdown and a successful health in the same minute,
            # which reads as nothing having happened.
            #
            # restart_delay spreads the retries so it stops competing with
            # ollama's own boot preload (deploy/ollama-classroom/ollama-preload.service),
            # which now retries for the same reason. start_period gives the app
            # room to load its weights before a slow first response counts as a
            # failed healthcheck.
            "restart": "unless-stopped",
            "restart_delay": "30s",
            "healthcheck": {
                "test": ["CMD-SHELL", "curl -sf http://localhost:17493/health || exit 1"],
                "interval": "30s",
                "timeout": "10s",
                # Loading weights for a TTS model off disk takes minutes on a
                # cold page cache; without this Docker kills it mid-load.
                "start_period": "300s",
                "retries": 3,
            },
        }

        # Prefer the published image; fall back to building from the git context.
        #
        # BOTH keys are emitted deliberately, which is what makes compose try the
        # pull first and only build if it fails. The hazard is that a failed pull
        # drops the operator into a silent 10-20 minute compile — so
        # `pre_start` says so explicitly, and the other four custom-image services
        # use the same pattern.
        image = getattr(config, "image", None)
        if image:
            service["image"] = image
        service["build"] = {"context": self._build_context(config)}

        deploy = self.gpu_reservation(config.gpu)
        if deploy:
            service["deploy"] = deploy

        return {"voicebox": service}

    def pre_start(self, config: ServiceConfig, data_dir: str) -> None:
        """Warn when `up` is about to compile voicebox from source.

        Normally this doesn't happen: build-images.yml publishes a prebuilt image
        and compose pulls it. It falls back to building only when that pull
        fails — no such tag yet, no arm64 build, or the registry is
        unreachable. That build pulls a full torch/CUDA stack and takes a long
        time with no output for minutes at a stretch, so a first-time user
        reasonably concludes it has hung. Only fires when the image is genuinely
        absent, so routine restarts stay quiet.
        """
        if getattr(config, "image", None):
            try:
                probe = subprocess.run(
                    ["docker", "image", "inspect", config.image],
                    capture_output=True,
                    timeout=10,
                )
                if probe.returncode == 0:
                    return  # already have it — this will be a fast pull at worst
            except (OSError, subprocess.SubprocessError):
                return  # can't tell; compose will surface any real error

            console.print(
                f"  [yellow]Note:[/yellow] {config.image} is not present locally; "
                f"composepull will fetch it.\n"
                f"  If that pull fails, docker will [bold]compile from source[/bold] "
                f"(10-20 min, long silent stretches)."
            )
            return

        try:
            probe = subprocess.run(
                ["docker", "image", "inspect", "puente-voicebox"],
                capture_output=True,
                timeout=10,
            )
            built = probe.returncode == 0
        except (OSError, subprocess.SubprocessError):
            return  # no docker / can't tell — compose will surface any real error

        if built:
            return

        console.print(
            "  [yellow]First run:[/yellow] voicebox has no prebuilt image, so it is "
            "compiled from source now\n"
            "  (torch + CUDA — expect [bold]10-20 minutes[/bold] and long silent "
            "stretches). This is a [bold]one-off[/bold];\n"
            "  later starts reuse the built image and come up in seconds."
        )
