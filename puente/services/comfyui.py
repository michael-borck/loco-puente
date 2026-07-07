"""ComfyUI — local image generation (Docker with GPU)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from rich.console import Console

from puente.models import ComfyUIConfig, ServiceConfig

from .base import ServiceBase

console = Console()

# Written to {data_dir}/comfyui-run/user_script.bash — runs before the mmartial
# upgrade loop (early startup hook: clone Manager, write config).
_STARTUP_SCRIPT = """#!/bin/bash
# Puente ComfyUI early setup — clones Manager before ComfyUI starts.

MANAGER_REPO="https://github.com/ltdrdata/ComfyUI-Manager.git"
MANAGER_DIR="/basedir/custom_nodes/ComfyUI-Manager"

# Clone or update ComfyUI-Manager.
mkdir -p /basedir/custom_nodes
if [ ! -d "$MANAGER_DIR" ]; then
    git clone --depth 1 "$MANAGER_REPO" "$MANAGER_DIR" 2>&1 || true
else
    git -C "$MANAGER_DIR" pull --quiet 2>&1 || true
fi

# Write Manager config (always overwrite to keep settings correct).
if [ -d "$MANAGER_DIR" ]; then
    cat > "$MANAGER_DIR/config.ini" << 'CONFIGEOF'
[default]
channel_url = local
preview_method = auto
badge_mode = none
git_exe =
update_interval = 600
enable_after_install = False
network_mode = public
security_level = weak
CONFIGEOF
fi
"""

# Written to {data_dir}/comfyui-run/postvenv_script.bash — runs AFTER the mmartial
# upgrade loop (so our setuptools pin isn't overwritten) but before torch/ComfyUI.
_POSTVENV_SCRIPT = """#!/bin/bash
# Puente ComfyUI post-upgrade setup — runs after mmartial's package upgrade loop.

VENV_PIP="/comfy/mnt/venv/bin/pip"

# Pin setuptools<70: mmartial upgrades to 82.x which omits pkg_resources from
# uv venvs. Many custom nodes import pkg_resources at load time.
# NOTE: do NOT install custom node requirements here — this hook runs before torch,
# so compiled extensions (scikit-image, opencv, etc.) would be built against the
# wrong numpy ABI. Use ComfyUI-Manager's "Try Fix" button for nodes with compiled deps.
if [ -f "$VENV_PIP" ]; then
    "$VENV_PIP" install "setuptools<70" --quiet 2>&1 || true

    # numpy-2 ABI fix: the base image ships numpy 2.x but pins old
    # scikit-learn (1.1.x) and scikit-image (0.19.x) built against numpy 1.x.
    # Their compiled extensions (sklearn murmurhash, skimage geometry) raise
    # "numpy.dtype size changed (96 vs 88)" when transitively imported — which
    # breaks SwarmUI's ComfyUI backend nodes (SwarmComfyCommon) at load time.
    # Upgrading to numpy-2-compatible builds resolves it. These are upgrades of
    # existing packages, not new compiled builds, so ABI-safe to run pre-torch.
    "$VENV_PIP" install --upgrade "scikit-learn>=1.4" "scikit-image>=0.24" --quiet 2>&1 || true
fi
"""


# --- Optional SadTalker (talking-head) support ------------------------------
# The Comfyui-SadTalker node is 2020-era code that breaks on this image's
# modern numpy/torchvision. Three source-level fixes + a weights download make
# it run. Gated behind ComfyUIConfig.install_sadtalker (off by default: ~2.4GB
# of weights). Applied in post_start, idempotently. See docs/sadtalker-api.md.
_SADTALKER_DIR = "/basedir/custom_nodes/Comfyui-SadTalker"

# Bash run INSIDE the comfyui container (as root) to patch node source, create
# a torchvision shim, and download weights only when missing. Idempotent.
_SADTALKER_SETUP = r"""#!/bin/bash
set -u
ST="/basedir/custom_nodes/Comfyui-SadTalker"
PY="/comfy/mnt/venv/bin/python"
[ -d "$ST" ] || { echo "SadTalker node not present, skipping"; exit 0; }

# 1. preprocess.py: np.VisibleDeprecationWarning was removed in numpy 2.
PP="$ST/SadTalker/src/face3d/util/preprocess.py"
if [ -f "$PP" ] && grep -q 'category=np.VisibleDeprecationWarning' "$PP"; then
    sed -i 's/category=np.VisibleDeprecationWarning/category=getattr(np, "VisibleDeprecationWarning", DeprecationWarning)/' "$PP"
    echo "patched preprocess.py"
fi

# 2. ShowVideo.py: crashes in API mode when extra_pnginfo[0] is None.
SV="$ST/nodes/ShowVideo.py"
if [ -f "$SV" ] && grep -q 'and "workflow" in extra_pnginfo\[0\]:' "$SV" \
   && ! grep -q 'extra_pnginfo\[0\] and "workflow"' "$SV"; then
    sed -i 's/and "workflow" in extra_pnginfo\[0\]:/and extra_pnginfo[0] and "workflow" in extra_pnginfo[0]:/' "$SV"
    echo "patched ShowVideo.py"
fi

# 3. torchvision.transforms.functional_tensor shim (removed in tv 0.17+, old
#    basicsr still imports rgb_to_grayscale from it).
"$PY" - <<'PYEOF'
import os, torchvision
shim = os.path.join(os.path.dirname(torchvision.__file__), "transforms", "functional_tensor.py")
if not os.path.exists(shim):
    open(shim, "w").write(
        "# Shim: functional_tensor removed in torchvision 0.17+; old basicsr imports it.\n"
        "from torchvision.transforms.functional import rgb_to_grayscale\n")
    print("created torchvision functional_tensor shim")
PYEOF

# 4. Weights (~2.4GB) — download only what's missing.
CKPT="$ST/SadTalker/checkpoints"; GFP="/basedir/gfpgan/weights"
mkdir -p "$CKPT" "$GFP"
dl() { [ -s "$2" ] || { echo "downloading $(basename "$2")"; wget -nc -q "$1" -O "$2" || true; }; }
BASE="https://github.com/OpenTalker/SadTalker/releases/download/v0.0.2-rc"
dl "$BASE/mapping_00109-model.pth.tar"        "$CKPT/mapping_00109-model.pth.tar"
dl "$BASE/mapping_00229-model.pth.tar"        "$CKPT/mapping_00229-model.pth.tar"
dl "$BASE/SadTalker_V0.0.2_256.safetensors"   "$CKPT/SadTalker_V0.0.2_256.safetensors"
dl "$BASE/SadTalker_V0.0.2_512.safetensors"   "$CKPT/SadTalker_V0.0.2_512.safetensors"
dl "https://github.com/xinntao/facexlib/releases/download/v0.1.0/alignment_WFLW_4HG.pth"      "$GFP/alignment_WFLW_4HG.pth"
dl "https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth" "$GFP/detection_Resnet50_Final.pth"
dl "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.0/GFPGANv1.4.pth"              "$GFP/GFPGANv1.4.pth"
dl "https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth"        "$GFP/parsing_parsenet.pth"
echo "SADTALKER_SETUP_DONE"
"""


# --- Optional Wav2Lip (video-driven lip-sync) support -----------------------
# Wav2Lip is the light, 8GB-friendly video->video lip-sync path (vs LatentSync
# which needs ~20GB). Installs two nodes: ComfyUI_wav2lip (the sync engine) and
# ComfyUI-VideoHelperSuite (VHS_LoadVideo / VHS_VideoCombine for real video I/O).
# Gated behind ComfyUIConfig.install_wav2lip. See docs/wav2lip-api.md.
_WAV2LIP_SETUP = r"""#!/bin/bash
set -u
CN="/basedir/custom_nodes"
PY="/comfy/mnt/venv/bin/python"
PIP="/comfy/mnt/venv/bin/pip"

# 1. Clone the two nodes if missing.
[ -d "$CN/ComfyUI_wav2lip" ] || git clone --depth 1 https://github.com/ShmuelRonen/ComfyUI_wav2lip.git "$CN/ComfyUI_wav2lip" 2>&1 | tail -1
[ -d "$CN/ComfyUI-VideoHelperSuite" ] || git clone --depth 1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git "$CN/ComfyUI-VideoHelperSuite" 2>&1 | tail -1

# 2. VideoHelperSuite requirements (opencv already present; imageio-ffmpeg needed).
if [ -f "$CN/ComfyUI-VideoHelperSuite/requirements.txt" ]; then
    "$PIP" install -r "$CN/ComfyUI-VideoHelperSuite/requirements.txt" --quiet 2>&1 | tail -2 || true
fi

# 3. Wav2Lip GAN weight (~416MB). The S3FD face detector weight auto-downloads
#    on first inference, so only the GAN model needs fetching here.
CKPT="$CN/ComfyUI_wav2lip/Wav2Lip/checkpoints"
mkdir -p "$CKPT"
if [ ! -s "$CKPT/wav2lip_gan.pth" ]; then
    echo "downloading wav2lip_gan.pth"
    wget -nc -q "https://huggingface.co/Nekochu/Wav2Lip/resolve/main/wav2lip_gan.pth?download=true" -O "$CKPT/wav2lip_gan.pth" || true
fi
echo "WAV2LIP_SETUP_DONE"
"""


class ComfyUIService(ServiceBase):
    name = "comfyui"
    description = "Image generation (SD 1.5, SDXL, FLUX)"
    default_port = 8188
    install_method = "docker"
    docker_image = "ghcr.io/michael-borck/puente-comfyui:latest"
    requires_gpu = True

    def pre_start(self, config: ServiceConfig, data_dir: str) -> None:
        if not isinstance(config, ComfyUIConfig) or not config.install_manager:
            return
        run_dir = Path(data_dir) / "comfyui-run"
        run_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in [
            ("user_script.bash", _STARTUP_SCRIPT),
            ("postvenv_script.bash", _POSTVENV_SCRIPT),
        ]:
            script = run_dir / filename
            script.write_text(content)
            script.chmod(0o755)

    def post_start(self, config: ServiceConfig, data_dir: str) -> None:
        """Optionally install the SadTalker and/or Wav2Lip avatar add-ons.

        Both are gated on their own ComfyUIConfig flags (default False) and
        install/patch nodes + download weights via idempotent container-side
        scripts, so re-running is cheap (skips applied patches and present
        weights). If either runs, comfyui is restarted once at the end so the
        new/patched nodes re-import. See docs/sadtalker-api.md, docs/wav2lip-api.md.
        """
        if not isinstance(config, ComfyUIConfig):
            return

        changed = False

        if config.install_sadtalker:
            node_dir = Path(data_dir) / "comfyui-basedir" / "custom_nodes" / "Comfyui-SadTalker"
            if not node_dir.exists():
                console.print(
                    "[yellow]install_sadtalker is set but the Comfyui-SadTalker node "
                    "is not present in custom_nodes; install it via ComfyUI-Manager "
                    "first, then re-run.[/yellow]"
                )
            elif self._run_setup("SadTalker (fixes + ~2.4GB weights)", _SADTALKER_SETUP, "SADTALKER_SETUP_DONE"):
                changed = True

        if config.install_wav2lip:
            if self._run_setup("Wav2Lip + VideoHelperSuite (nodes + ~416MB weight)", _WAV2LIP_SETUP, "WAV2LIP_SETUP_DONE"):
                changed = True

        if changed:
            console.print("  [cyan]Restarting comfyui to load the new/patched nodes.[/cyan]")
            subprocess.run(["docker", "restart", "puente-comfyui"], capture_output=True, text=True)

    def _run_setup(self, label: str, script: str, done_marker: str) -> bool:
        """Run a container-side setup script; return True on success."""
        console.print(f"  [cyan]Setting up {label}...[/cyan]")
        result = subprocess.run(
            ["docker", "exec", "-u", "0", "puente-comfyui", "bash", "-c", script],
            capture_output=True,
            text=True,
        )
        if done_marker not in result.stdout:
            console.print(
                f"[yellow]{label} did not complete cleanly:[/yellow]\n"
                f"{result.stdout[-500:]}\n{result.stderr[-500:]}"
            )
            return False
        return True

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = {
            "USE_UV": "true",
            "WANTED_UID": "1000",
            "WANTED_GID": "1000",
            "BASE_DIRECTORY": "/basedir",
            "SECURITY_LEVEL": "weak",
        }
        env.update(config.environment)

        fragment: dict[str, Any] = {
            "comfyui": {
                "image": self.docker_image,
                "build": {"context": "./dockerfiles/comfyui"},
                "container_name": "puente-comfyui",
                "ports": [f"{port}:8188"],
                "volumes": [
                    f"{data_dir}/comfyui-run:/comfy/mnt",
                    f"{data_dir}/comfyui-basedir:/basedir",
                    f"{data_dir}/comfyui-basedir/custom_nodes:/comfy/ComfyUI/custom_nodes",
                ],
                "environment": env,
                "init": True,
                "restart": "unless-stopped",
            }
        }

        if config.gpu is not None:
            fragment["comfyui"]["deploy"] = {
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
