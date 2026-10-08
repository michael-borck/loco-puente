"""GPU detection via nvidia-smi."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table


@dataclass
class GPU:
    index: int
    name: str
    vram_mb: int
    driver: str
    compute_cap: str
    #: Stable hardware identity, e.g. "GPU-15c8ed7d-...". Unlike `index`, this
    #: does not change when cards are reordered, a second card is added, or the
    #: box reboots into a different enumeration order. Empty when nvidia-smi
    #: didn't report one (very old drivers), which disables UUID pinning.
    uuid: str = ""

    @property
    def vram_gb(self) -> float:
        return self.vram_mb / 1024

    @property
    def identifier(self) -> str:
        """What to write into a `gpu:` pin.

        Prefers the UUID, because an index silently points at a different card
        after a hardware change. Falls back to the index only when no UUID is
        available, which is strictly worse but still better than pinning nothing.
        """
        return self.uuid or str(self.index)

    def short_uuid(self) -> str:
        """UUID without the `GPU-` prefix, for display."""
        return self.uuid.removeprefix("GPU-")


def detect_gpus() -> list[GPU]:
    """Query nvidia-smi for available GPUs."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,uuid,name,memory.total,driver_version,compute_cap",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []

    if result.returncode != 0:
        return []

    gpus = []
    for line in result.stdout.strip().splitlines():
        parts = [p.strip() for p in line.split(",")]
        if len(parts) >= 6:
            gpus.append(
                GPU(
                    index=int(parts[0]),
                    uuid=parts[1],
                    name=parts[2],
                    vram_mb=int(parts[3]),
                    driver=parts[4],
                    compute_cap=parts[5],
                )
            )
    return gpus


def suggest_gpu_assignment(gpus: list[GPU]) -> dict[str, str | None]:
    """Suggest GPU assignments based on VRAM.

    Returns a dict mapping role -> GPU identifier (UUID when available, else
    index). Largest VRAM GPU gets primary LLM + images; the second gets voice and
    the secondary LLM.

    Assigning by identifier rather than index is the whole point: the generated
    puente.yml keeps pointing at the same physical card after the machine is
    re-enumerated.
    """
    if not gpus:
        return {"primary_llm": None, "images": None, "voice": None, "secondary_llm": None}

    sorted_gpus = sorted(gpus, key=lambda g: g.vram_mb, reverse=True)
    primary = sorted_gpus[0].identifier
    secondary = sorted_gpus[1].identifier if len(gpus) > 1 else primary

    return {
        "primary_llm": primary,
        "images": primary,
        "voice": secondary,
        "secondary_llm": secondary,
    }


def resolve_gpu(pin: str | int | None, gpus: list[GPU] | None = None) -> GPU | None:
    """Resolve a `gpu:` pin to a GPU.

    Accepts either an index (`1`, or the string `"1"`) or a UUID, with or without
    the `GPU-` prefix. Returns None when the pin is None or names hardware that
    isn't present.

    An index that doesn't exist is a hard miss rather than a fallback: silently
    resolving an unknown index to "some GPU" is exactly the wrong-card bug this
    whole mechanism exists to prevent.
    """
    if pin is None:
        return None

    gpus = gpus if gpus is not None else detect_gpus()
    if not gpus:
        return None

    needle = str(pin).strip()
    # Accept "ce79654c-..." as well as the full "GPU-ce79654c-...".
    bare = needle.removeprefix("GPU-").lower()

    for gpu in gpus:
        if needle.isdigit() and gpu.index == int(needle):
            return gpu
        if gpu.uuid and gpu.uuid.removeprefix("GPU-").lower() == bare:
            return gpu
    return None


def print_gpu_table(gpus: list[GPU]) -> None:
    """Print a Rich table of detected GPUs."""
    console = Console()

    if not gpus:
        console.print("[yellow]No NVIDIA GPUs detected[/yellow]")
        return

    table = Table(title="Detected GPUs")
    table.add_column("GPU", style="cyan")
    table.add_column("Name", style="bold")
    table.add_column("VRAM", justify="right")
    table.add_column("Compute", justify="right")
    table.add_column("UUID", style="dim")
    table.add_column("Driver")

    for gpu in gpus:
        table.add_row(
            str(gpu.index),
            gpu.name,
            f"{gpu.vram_gb:.0f} GB",
            gpu.compute_cap,
            gpu.short_uuid() or "—",
            gpu.driver,
        )

    console.print(table)
    console.print(
        "\n[dim]Pin with the UUID (`gpu: GPU-<uuid>`), not the index: indices are "
        "reassigned when cards are\nreordered or the box reboots, and a stale pin "
        "silently loads onto the wrong card.[/dim]"
    )
