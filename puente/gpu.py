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

    @property
    def vram_gb(self) -> float:
        return self.vram_mb / 1024


def detect_gpus() -> list[GPU]:
    """Query nvidia-smi for available GPUs."""
    try:
        result = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=index,name,memory.total,driver_version,compute_cap",
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
        if len(parts) >= 5:
            gpus.append(
                GPU(
                    index=int(parts[0]),
                    name=parts[1],
                    vram_mb=int(parts[2]),
                    driver=parts[3],
                    compute_cap=parts[4],
                )
            )
    return gpus


def suggest_gpu_assignment(gpus: list[GPU]) -> dict[str, int | None]:
    """Suggest GPU assignments based on VRAM.

    Returns a dict mapping role -> gpu index.
    Largest VRAM GPU gets primary LLM + images.
    Second GPU gets voice + secondary LLM.
    """
    if not gpus:
        return {"primary_llm": None, "images": None, "voice": None, "secondary_llm": None}

    sorted_gpus = sorted(gpus, key=lambda g: g.vram_mb, reverse=True)
    primary = sorted_gpus[0].index
    secondary = sorted_gpus[1].index if len(sorted_gpus) > 1 else primary

    return {
        "primary_llm": primary,
        "images": primary,
        "voice": secondary,
        "secondary_llm": secondary,
    }


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
    table.add_column("Driver")

    for gpu in gpus:
        table.add_row(
            str(gpu.index),
            gpu.name,
            f"{gpu.vram_gb:.0f} GB",
            gpu.compute_cap,
            gpu.driver,
        )

    console.print(table)
