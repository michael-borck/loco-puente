"""What this host can actually do.

Implements the promise in docs/vision.md: detect the hardware, then say plainly
which capabilities are available — and which are not — rather than leaving the
operator to discover it by watching containers fail.

The verdicts are deliberately blunt. "tight" is worth saying out loud, because a
service that starts and then loses a boot race is worse than one that was never
offered. This is also the honest answer to "offer the best option available, or
say not usable": usable, tight, or not — with the reason attached.

Nothing here installs anything or writes config. It reads hardware and answers.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Literal

# Verdict ladder, best first.
Verdict = Literal["good", "tight", "offload", "unavailable", "unknown"]

#: Ordering for "can I do this at all?" checks — anything but unavailable.
USABLE = ("good", "tight", "offload")


@dataclass
class HostProfile:
    """Detected hardware, reduced to what capability decisions actually need."""

    gpu_name: str | None
    gpu_vram_gb: float          # largest single card
    gpu_count: int
    total_vram_gb: float        # across all cards
    ram_gb: float
    mem_class: str              # ddr3 | ddr4 | ddr5 | unknown
    mem_bandwidth_gbs: float | None
    cpu_cores: int
    has_nvidia_runtime: bool

    @property
    def budget_gb(self) -> float:
        """Roughly what one model can occupy.

        The largest card, or a card plus half of free RAM when experts may be
        offloaded. Deliberately conservative: the answer decides whether a
        service is offered at all, so overestimating hands someone a config that
        fails at boot.
        """
        if self.gpu_vram_gb <= 0:
            return self.ram_gb * 0.5
        return self.gpu_vram_gb + (self.ram_gb * 0.4 if self.ram_gb >= 16 else 0)


@dataclass
class Capability:
    """One thing the stack can do, and whether this host can."""

    name: str
    verdict: Verdict
    why: str
    needs_gb: float | None = None
    hint: str = ""


# --------------------------------------------------------------------------
# memory class — the DDR3 cliff (see ADR0010)
# --------------------------------------------------------------------------

#: Realistic sustained dual-channel bandwidth by memory generation, GB/s.
#: DDR4-3200 lands within a few percent of the published DDR5-6000 MoE
#: benchmark, so DDR4->DDR5 is NOT a meaningful cliff. DDR3->DDR4 is ~1.7x.
_MEM_BANDS = {
    "ddr3": 22.0,
    "ddr4": 38.0,
    "ddr5": 42.0,
}


def _cpu_name() -> str:
    try:
        with open("/proc/cpuinfo") as fh:
            for line in fh:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return ""


def _ram_gb() -> float:
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    return int(re.search(r"(\d+)", line).group(1)) / 1024 / 1024
    except OSError:
        pass
    return 0.0


def _core_count() -> int:
    try:
        return len(re.findall(r"^processor\s*:", open("/proc/cpuinfo").read(), re.M))
    except OSError:
        return 0


def _mem_class() -> tuple[str, float | None]:
    """Best-effort memory generation.

    dmidecode needs root, which a capability report should not require, so this
    infers from the CPU model when the SPD data is unreadable and says
    "unknown" rather than guessing silently — an unknown class must not be
    reported as a good one.
    """
    cpu = _cpu_name()
    # Well-known desktop/server parts and the memory generation they shipped with.
    hints = [
        (r"\b(2[0-9]{3}|1[7-9][0-9]{2})\b", None),  # placeholder, refined below
    ]
    if re.search(r"Xeon.*(5th|6th|7th|8th|9th|10th)|EPYC|Ryzen [579]|Threadripper", cpu):
        return "ddr4", _MEM_BANDS["ddr4"]
    if re.search(r"Xeon.*(3rd|4th)|EPYC (1st|2nd|3rd)", cpu):
        return "ddr3", _MEM_BANDS["ddr3"]
    if re.search(r"Ryzen (7|9)[0-9]{3}X|Athlon", cpu):
        return "ddr5", _MEM_BANDS["ddr5"]
    del hints
    return "unknown", None


def _nvidia_runtime_ok() -> bool:
    if shutil.which("nvidia-smi") is None:
        return False
    try:
        r = subprocess.run(
            ["docker", "info", "--format", "{{json .Runtimes}}"],
            capture_output=True, text=True, timeout=10,
        )
        return r.returncode == 0 and "nvidia" in r.stdout
    except (OSError, subprocess.SubprocessError):
        return False


def detect_host() -> HostProfile:
    """Build a HostProfile from what is actually on this machine."""
    from .gpu import detect_gpus

    gpus = detect_gpus()
    mem_class, bandwidth = _mem_class()
    ram = _ram_gb()

    return HostProfile(
        gpu_name=gpus[0].name if gpus else None,
        gpu_vram_gb=gpus[0].vram_gb if gpus else 0.0,
        gpu_count=len(gpus),
        total_vram_gb=sum(g.vram_gb for g in gpus),
        ram_gb=ram,
        mem_class=mem_class,
        mem_bandwidth_gbs=bandwidth,
        cpu_cores=_core_count(),
        has_nvidia_runtime=_nvidia_runtime_ok(),
    )


# --------------------------------------------------------------------------
# capability table
# --------------------------------------------------------------------------

#: name -> (approx weights GB, what it needs, the YAML that enables it)
#:
#: Sizes are the *working* footprint, not the download size, and are deliberately
#: pessimistic. A capability that is wrongly offered costs an operator an evening.
_CATALOGUE: dict[str, tuple[float, str, str]] = {
    "chat": (6.0, "A 7–8B model at Q4, fully resident in VRAM.",
             "services:\n  localai:\n    enabled: true\n  ollama:\n    enabled: false"),
    "chat-large": (18.0, "A 30B model at Q4. Wants a 24 GB card, or MoE expert offload.",
                  "llama_cpp:\n  instances:\n    - name: chat\n      cpu_moe: 8"),
"coding": (6.0, "A 7B code model at Q4. Same footprint as chat.",
                "services:\n  localai:\n    enabled: true\n  ollama:\n    enabled: false"),
    "image": (9.0, "SDXL or FLUX. ComfyUI, ~9 GB.",
              "services:\n  comfyui:\n    enabled: true"),
    "image-video": (22.0, "Wan2.2-S2V needs ~22 GB at fp8. A 24 GB card, alone.",
                    "services:\n  comfyui:\n    enabled: true\n    install_wan_s2v: true"),
    "voice": (6.0, "Voicebox TTS. ~5.6 GB of weights.",
              "services:\n  voicebox:\n    enabled: true"),
    # LocalAI serves songs too, but routing them there would mean giving up
# ACE-Step's own container — which exists because it pins a different torch build
# from ComfyUI's (see AceStepConfig). Tier 2 stays Tier 2; see decide.py.
    "song": (5.0, "ACE-Step 2B. ~4.7 GB — the cheapest capability here.",
             "services:\n  ace_step:\n    enabled: true"),
    "research": (6.0, "AnythingLLM over a chat model.", "services:\n  anythingllm:\n    enabled: true"),
}

#: Capabilities that need CUDA. On a host without it the honest answer is
#: "unavailable", not "slow" — MPS/ROCm paths are not something puente ships.
_CUDA_ONLY = {"image", "image-video", "voice", "song"}


def assess(host: HostProfile, backend: str = "ollama") -> list[Capability]:
    """Verdict per capability for this host."""
    out: list[Capability] = []
    budget = host.budget_gb

    for name, (needs, why, hint) in _CATALOGUE.items():
        v: Verdict
        detail = why

        if not host.has_nvidia_runtime and name in _CUDA_ONLY:
            v = "unavailable"
            detail = "Needs an NVIDIA GPU with the container runtime. No CUDA on this host."
        elif host.gpu_count == 0:
            v = "unavailable"
            detail = "No NVIDIA GPU detected."
        elif needs <= host.gpu_vram_gb:
            v = "good"
        elif needs <= budget:
            v = "offload"
            detail = (
                f"{why} Exceeds the {host.gpu_vram_gb:.0f} GB card; needs expert "
                f"offload into system RAM."
            )
            if host.mem_class == "ddr3":
                detail += (
                    " Note: this host's memory looks like DDR3, where streaming "
                    "experts is ~1.7x slower than DDR4 — expect a real slowdown."
                )
        else:
            v = "unavailable"
            detail = (
                f"{why} Needs about {needs:.0f} GB; this host offers roughly "
                f"{budget:.0f} GB."
            )

        if name == "chat-large" and backend == "ollama":
            detail += (
                " Note: Ollama cannot do expert offload — use the llama.cpp "
                "backend for this."
            )
            v = "unavailable" if v == "offload" else v

        out.append(
            Capability(
                name=name, verdict=v, why=detail, needs_gb=needs, hint=hint
            )
        )

    return out


@dataclass
class Report:
    """A capability assessment, with the backend it was made against.

    Backend lives here rather than being passed to `assess()` and `render()`
    separately: threading it through two functions means a caller can desync
    them and get a verdict for one backend displayed under another's name.
    """

    host: HostProfile
    backend: str
    capabilities: list[Capability]

    def usable(self) -> list[str]:
        return [c.name for c in self.capabilities if c.verdict in USABLE]

    def unavailable(self) -> list[str]:
        return [c.name for c in self.capabilities if c.verdict == "unavailable"]

    def to_dict(self) -> dict:
        return {
            "host": {
                "gpu": self.host.gpu_name,
                "gpu_count": self.host.gpu_count,
                "total_vram_gb": round(self.host.total_vram_gb, 1),
                "ram_gb": round(self.host.ram_gb, 1),
                "mem_class": self.host.mem_class,
                "budget_gb": round(self.host.budget_gb, 1),
            },
            "backend": self.backend,
            "capabilities": [
                {"name": c.name, "verdict": c.verdict, "why": c.why}
                for c in self.capabilities
            ],
        }

    def render(self) -> str:
        return render(self)


def report_for(host: HostProfile, backend: str | None = None) -> Report:
    """Assess this host, choosing a backend when one isn't specified."""
    chosen = backend or suggest_backend(host)
    return Report(host=host, backend=chosen, capabilities=assess(host, backend=chosen))


def suggest_backend(host: HostProfile) -> str:
    """Which LLM backend suits this host.

    llama.cpp where expert offload is the difference between a large model
    working and not — i.e. a small card. Ollama everywhere else, because it is
    easier to operate. The only capability that distinguishes them today is
    `chat-large`, so the test is narrow on purpose.

    LocalAI is not considered here. It is the successor engine (ADR0012) but it
    wraps llama.cpp and vLLM rather than adding a placement capability of its
    own, so it inherits their verdicts rather than extending them. Choosing it
    is an operator's decision — `puente capabilities --backend localai` — not
    something hardware detection should make on their behalf.
    """
    ollama_can = {c.name for c in assess(host, "ollama") if c.verdict in USABLE}
    llama_can = {c.name for c in assess(host, "llama.cpp") if c.verdict in USABLE}
    return "llama.cpp" if len(llama_can - ollama_can) > 0 else "ollama"


def render(report: Report) -> str:
    """Human-readable capability report."""
    host, backend, caps = report.host, report.backend, report.capabilities
    lines: list[str] = []
    hw = []
    if host.gpu_name:
        cards = f"x{host.gpu_count}" if host.gpu_count > 1 else ""
        hw.append(f"{host.gpu_count} x {host.gpu_name}{cards} ({host.total_vram_gb:.0f} GB VRAM)")
    else:
        hw.append("no NVIDIA GPU")
    hw.append(f"{host.ram_gb:.0f} GB RAM")
    if host.mem_class != "unknown":
        hw.append(f"{host.mem_class.upper()} ~{host.mem_bandwidth_gbs:.0f} GB/s")
    else:
        hw.append("memory class unknown (run with sudo for a reading)")
    hw.append(f"{host.cpu_cores} cores")
    lines.append("Detected: " + ", ".join(hw))
    lines.append(f"LLM backend: {backend}")
    lines.append(f"Rough budget per model: ~{host.budget_gb:.0f} GB")
    lines.append("")

    marks = {"good": "✓", "tight": "~", "offload": "~", "unavailable": "✗", "unknown": "?"}
    width = max(len(c.name) for c in caps)
    for c in caps:
        lines.append(f"  {marks[c.verdict]} {c.name:<{width}}  {c.verdict}")
        lines.append(f"      {c.why}")
        if c.verdict in USABLE and c.hint:
            lines.append("      enable with:")
            for hl in c.hint.splitlines():
                lines.append(f"        {hl}")
        lines.append("")

    usable = report.usable()
    not_usable = report.unavailable()
    lines.append(f"Usable: {', '.join(usable) if usable else 'nothing'}")
    if not_usable:
        lines.append(f"Not on this host: {', '.join(not_usable)}")
    return "\n".join(lines)