"""SwarmUI — friendly image-gen front-end that uses ComfyUI as the backend."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path
from typing import Any

from rich.console import Console

from puente.models import ServiceConfig

from .base import ServiceBase

console = Console()

# SwarmUI ships custom ComfyUI nodes (SwarmComfyCommon + SwarmComfyExtra) that
# its backend requires. When SwarmUI self-starts ComfyUI it injects them
# automatically; with an EXTERNAL ComfyUI (our puente-comfyui) it cannot, so
# ComfyUI logs "missing the Swarm core nodes" and generation fails. The
# post_start hook copies them out of the swarmui image into the shared ComfyUI
# custom_nodes volume. Source path inside the SwarmUI container:
_SWARM_NODES_SRC = "/SwarmUI/src/BuiltinExtensions/ComfyUIBackend/ExtraNodes"
_SWARM_NODE_DIRS = ("SwarmComfyCommon", "SwarmComfyExtra")

# SwarmComfyCommon/__init__.py imports every node eagerly, so one broken node
# takes down the whole package. Two optional segmentation nodes (SwarmClipSeg,
# SwarmSam2) fail on the shipped transformers 5.x (top-level CLIPSeg removed) —
# neither is needed for text-to-image. This patched __init__ guards those two
# so the core KSampler/Latents/SaveImage nodes still load. Overwrites the
# shipped file each run (idempotent, deterministic).
_SWARM_COMMON_INIT = '''\
import os, folder_paths

# Core Swarm nodes required for text-to-image generation. These must import.
from . import (
    SwarmBlending, SwarmImages, SwarmInternalUtil, SwarmKSampler,
    SwarmLoadImageB64, SwarmLoraLoader, SwarmMasks, SwarmSaveImageWS,
    SwarmTiling, SwarmExtractLora, SwarmUnsampler, SwarmLatents,
    SwarmInputNodes, SwarmTextHandling, SwarmReference, SwarmMath, SwarmAudio,
)

# Optional nodes with heavy/incompatible deps (transformers CLIPSeg, SAM2).
# The shipped ComfyUI has transformers 5.x which removed the top-level CLIPSeg
# imports these rely on. Guard them so one broken optional node does not take
# down the whole package (and thus core generation).
_optional = []
try:
    from . import SwarmClipSeg
    _optional.append(SwarmClipSeg)
except Exception as _e:  # noqa: BLE001
    print(f"[SwarmComfyCommon] optional SwarmClipSeg disabled: {type(_e).__name__}: {str(_e)[:120]}")
try:
    from . import SwarmSam2
    _optional.append(SwarmSam2)
except Exception as _e:  # noqa: BLE001
    print(f"[SwarmComfyCommon] optional SwarmSam2 disabled: {type(_e).__name__}: {str(_e)[:120]}")

WEB_DIRECTORY = "./web"

NODE_CLASS_MAPPINGS = (
    SwarmBlending.NODE_CLASS_MAPPINGS
    | SwarmImages.NODE_CLASS_MAPPINGS
    | SwarmInternalUtil.NODE_CLASS_MAPPINGS
    | SwarmKSampler.NODE_CLASS_MAPPINGS
    | SwarmLoadImageB64.NODE_CLASS_MAPPINGS
    | SwarmLoraLoader.NODE_CLASS_MAPPINGS
    | SwarmMasks.NODE_CLASS_MAPPINGS
    | SwarmSaveImageWS.NODE_CLASS_MAPPINGS
    | SwarmTiling.NODE_CLASS_MAPPINGS
    | SwarmExtractLora.NODE_CLASS_MAPPINGS
    | SwarmUnsampler.NODE_CLASS_MAPPINGS
    | SwarmLatents.NODE_CLASS_MAPPINGS
    | SwarmInputNodes.NODE_CLASS_MAPPINGS
    | SwarmTextHandling.NODE_CLASS_MAPPINGS
    | SwarmReference.NODE_CLASS_MAPPINGS
    | SwarmMath.NODE_CLASS_MAPPINGS
    | SwarmAudio.NODE_CLASS_MAPPINGS
)
for _mod in _optional:
    NODE_CLASS_MAPPINGS = NODE_CLASS_MAPPINGS | _mod.NODE_CLASS_MAPPINGS

def register_model_folder(name):
    if name not in folder_paths.folder_names_and_paths:
        folder_paths.folder_names_and_paths[name] = ([os.path.join(folder_paths.models_dir, name)], folder_paths.supported_pt_extensions)
    else:
        folder_paths.folder_names_and_paths[name] = (folder_paths.folder_names_and_paths[name][0], folder_paths.supported_pt_extensions)

register_model_folder("yolov8")
'''


# FDS (Frenetic Data Syntax) config telling SwarmUI to use a single
# external ComfyUI backend pointed at the puente-comfyui container.
# Format derived from SwarmUI's own BackendHandler.cs save logic and the
# ComfyUIAPISettings C# class. The "comfyui_api" type is the registered
# ID for the "ComfyUI API By URL" backend; without this file SwarmUI
# defaults to spinning up its own bundled ComfyUI instance and downloads
# multi-GB of duplicate models.
BACKENDS_FDS_CONTENT = """\
0:
    type: comfyui_api
    title: External ComfyUI (puente-comfyui)
    enabled: true
    settings:
        Address: http://puente-comfyui:8188
        AllowIdle: false
        OverQueue: 1
        EnableFrontendDev: false
"""


class SwarmUIService(ServiceBase):
    name = "swarmui"
    description = "Friendly image generation UI (uses ComfyUI backend)"
    default_port = 7801
    install_method = "docker"
    # Pull-first, build-fallback. Built and pushed to GHCR by the
    # .github/workflows/build-images.yml workflow. Configure SwarmUI to
    # talk to the existing puente-comfyui container instead of spinning
    # up its own bundled ComfyUI via the UI settings on first run.
    docker_image = "ghcr.io/michael-borck/puente-swarmui:latest"
    requires_gpu = True

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = dict(config.environment)

        fragment: dict[str, Any] = {
            "swarmui": {
                "image": self.docker_image,
                "build": {"context": "./dockerfiles/swarmui"},
                "container_name": "puente-swarmui",
                "ports": [f"{port}:7801"],
                "volumes": [
                    f"{data_dir}/swarmui:/SwarmUI/Data",
                    # Share ComfyUI's model tree so SwarmUI lists the same
                    # checkpoints/loras/vae instead of an empty folder. SwarmUI
                    # uses Stable-Diffusion/Lora/VAE dir names; ComfyUI uses
                    # checkpoints/loras/vae — map each explicitly. NOT read-only:
                    # SwarmUI writes .tmp hash-cache files alongside models
                    # (GetOrGenerateTensorHashSha256), which fails on a ro mount.
                    f"{data_dir}/comfyui-basedir/models/checkpoints:/SwarmUI/Models/Stable-Diffusion",
                    f"{data_dir}/comfyui-basedir/models/loras:/SwarmUI/Models/Lora",
                    f"{data_dir}/comfyui-basedir/models/vae:/SwarmUI/Models/VAE",
                ],
                "environment": env,
                "restart": "unless-stopped",
                # Wait for ComfyUI to pass its healthcheck before starting. Our
                # backend is an EXTERNAL ComfyUI by URL; if SwarmUI probes it
                # before the Swarm core nodes finish importing, the backend
                # latches into `errored` and every request returns "No backends
                # available!" until a manual RestartBackends. Gating startup on
                # comfyui's health closes that race on `puente up`. (NOTE: this
                # only orders a single compose-up — after a bare host reboot each
                # container restarts independently via its restart policy, so if
                # the error recurs, re-init via SwarmUI's RestartBackends API or
                # `docker restart puente-swarmui` once comfyui is up.)
                "depends_on": {
                    "comfyui": {"condition": "service_healthy"},
                },
            }
        }

        if config.gpu is not None:
            fragment["swarmui"]["deploy"] = {
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

    def pre_start(self, config: ServiceConfig, data_dir: str) -> None:
        """Pre-seed Backends.fds so SwarmUI uses puente-comfyui instead of
        downloading its own bundled ComfyUI on first launch. Idempotent —
        only writes the file if it doesn't already exist, so any user
        customisation via the SwarmUI UI is preserved across restarts.
        """
        backends_file = Path(data_dir) / "swarmui" / "Backends.fds"
        if backends_file.exists():
            return
        backends_file.parent.mkdir(parents=True, exist_ok=True)
        backends_file.write_text(BACKENDS_FDS_CONTENT)
        console.print(
            f"  [cyan]Pre-seeded SwarmUI external ComfyUI backend:[/cyan] {backends_file}"
        )

    def post_start(self, config: ServiceConfig, data_dir: str) -> None:
        """Install SwarmUI's ComfyUI backend nodes into the external
        puente-comfyui so it can actually drive generation.

        SwarmUI only auto-injects its nodes into a ComfyUI it self-starts; with
        an external backend we must copy them ourselves. We pull them out of the
        running swarmui container (docker cp) into ComfyUI's shared custom_nodes
        volume, patch SwarmComfyCommon/__init__.py to disable the two optional
        segmentation nodes that break on the shipped transformers, then restart
        comfyui so it re-imports. Idempotent: the __init__ is always rewritten to
        the known-good version; node dirs are re-copied only if missing.
        """
        custom_nodes = Path(data_dir) / "comfyui-basedir" / "custom_nodes"
        common_init = custom_nodes / "SwarmComfyCommon" / "__init__.py"

        # Fast path: nodes present and __init__ already patched → skip the
        # (slow) node install/comfyui-restart, but STILL reconcile the backend.
        # This is the common cold-boot case — nodes are already installed from
        # first setup, yet the backend may have latched `errored` in the reboot
        # race — so we must not early-return before reconcile_backends().
        already = (
            common_init.exists()
            and "optional SwarmClipSeg disabled" in common_init.read_text()
        )
        if already:
            self.reconcile_backends()
            return

        custom_nodes.mkdir(parents=True, exist_ok=True)
        copied_any = False
        for node_dir in _SWARM_NODE_DIRS:
            dest = custom_nodes / node_dir
            if dest.exists():
                continue
            result = subprocess.run(
                ["docker", "cp", f"puente-swarmui:{_SWARM_NODES_SRC}/{node_dir}", str(dest)],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                console.print(
                    f"[yellow]Could not copy Swarm node '{node_dir}' from puente-swarmui: "
                    f"{result.stderr.strip()}[/yellow]"
                )
                return
            copied_any = True

        # Always write the known-good patched __init__ (guards optional nodes).
        if (custom_nodes / "SwarmComfyCommon").exists():
            common_init.write_text(_SWARM_COMMON_INIT)
            console.print(
                "  [cyan]Installed SwarmUI backend nodes into ComfyUI custom_nodes.[/cyan]"
            )

        # Restart comfyui so it re-imports the newly installed nodes.
        if copied_any or common_init.exists():
            subprocess.run(
                ["docker", "restart", "puente-comfyui"],
                capture_output=True,
                text=True,
            )

        # Self-heal the external-ComfyUI backend if it latched `errored`.
        self.reconcile_backends()

    def reconcile_backends(self, retries: int = 30) -> None:
        """Recover SwarmUI's external-ComfyUI backend if it latched `errored`.

        SwarmUI probes its external ComfyUI backend once at startup. If it wins
        the race against ComfyUI finishing its node imports, it marks the backend
        `errored` and NEVER auto-retries — every generate then returns "No
        backends available!". `depends_on: service_healthy` closes this on a
        single `docker compose up`, but a bare host reboot restarts each
        container independently via its restart policy, bypassing that ordering,
        so the race recurs on cold boot. This runs SwarmUI's own RestartBackends
        API (idempotent: a no-op when the backend is already `running`), which is
        what fires on every `puente up` and — via the boot systemd unit — once
        per cold boot.

        All calls go through localhost inside puente-swarmui (docker exec + curl)
        so no host-side HTTP client or auth token is needed. The API demands a
        JSON content-type or it 400s "Wrong content type".
        """

        def _api(path: str, session: str = "") -> str:
            body = f'{{"session_id":"{session}"}}' if session else "{}"
            result = subprocess.run(
                [
                    "docker", "exec", "puente-swarmui",
                    "curl", "-s", "-X", "POST",
                    f"http://localhost:7801/API/{path}",
                    "-H", "Content-Type: application/json",
                    "-d", body,
                ],
                capture_output=True,
                text=True,
            )
            return result.stdout if result.returncode == 0 else ""

        # SwarmUI may still be booting its web server right after container
        # start; poll GetNewSession until it answers before we probe backends.
        session = ""
        for _ in range(retries):
            resp = _api("GetNewSession")
            if '"session_id"' in resp:
                session = resp.split('"session_id":"', 1)[1].split('"', 1)[0]
                break
            time.sleep(2)
        if not session:
            console.print(
                "[yellow]SwarmUI did not answer GetNewSession; skipping backend "
                "reconcile. Run `puente up swarmui` once it is up.[/yellow]"
            )
            return

        backends = _api("ListBackends", session)
        if '"status":"errored"' not in backends:
            return  # already running (or none configured) — nothing to do.

        console.print(
            "  [cyan]SwarmUI backend is errored (startup race); "
            "calling RestartBackends...[/cyan]"
        )
        _api("RestartBackends", session)

        # Poll until the backend leaves the errored state (or we give up).
        for _ in range(retries):
            time.sleep(2)
            backends = _api("ListBackends", session)
            if '"status":"running"' in backends:
                console.print("  [green]SwarmUI backend recovered (running).[/green]")
                return
            if '"status":"errored"' not in backends:
                return
        console.print(
            "[yellow]SwarmUI backend still not running after RestartBackends. "
            "Is puente-comfyui healthy? Check `docker ps`.[/yellow]"
        )
