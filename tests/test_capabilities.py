"""Tests for the capability report.

The report's job is to answer "can this host do X?" *before* an operator finds
out by watching a container fail. So the cases that matter are the boundaries:
a model that just fits, one that just does not, and hosts with no GPU at all.

Verdicts are deliberately pessimistic. A capability wrongly offered costs
someone an evening; one wrongly withheld costs them a capability.
"""

from __future__ import annotations

import pytest

from puente.capabilities import HostProfile, assess, report_for, suggest_backend


def host(**kw) -> HostProfile:
    base = dict(
        gpu_name="NVIDIA GeForce RTX 3090",
        gpu_vram_gb=24.0,
        gpu_count=1,
        total_vram_gb=24.0,
        ram_gb=32.0,
        mem_class="ddr4",
        mem_bandwidth_gbs=38.0,
        cpu_cores=8,
        has_nvidia_runtime=True,
    )
    base.update(kw)
    return HostProfile(**base)


def verdict(h: HostProfile, name: str, backend: str = "ollama") -> str:
    return next(c.verdict for c in assess(h, backend) if c.name == name)


# --------------------------------------------------------------------------
# the boundary
# --------------------------------------------------------------------------


def test_model_that_fits_is_good():
    h = host(gpu_vram_gb=24.0, ram_gb=32.0)
    assert verdict(h, "chat") == "good"


def test_model_needing_offload_is_labelled_offload_not_good():
    """The distinction that matters: 'runs, with a caveat' is not 'runs'.

    Mislabelling it good is how a service starts and then loses a boot race.
    """
    # 22 GB of video weights against a 16 GB card + 16 GB RAM.
    h = host(gpu_vram_gb=16.0, total_vram_gb=16.0, ram_gb=16.0)
    assert verdict(h, "image-video") == "offload"


def test_model_that_cannot_fit_is_unavailable():
    h = host(gpu_vram_gb=8.0, total_vram_gb=8.0, ram_gb=8.0)
    assert verdict(h, "chat-large") == "unavailable"


def test_unavailable_explains_the_shortfall():
    """A bare 'unavailable' leaves the reader guessing. The reason is the point."""
    h = host(gpu_vram_gb=8.0, total_vram_gb=8.0, ram_gb=8.0)
    why = next(c.why for c in assess(h) if c.name == "chat-large")
    assert "18 GB" in why and "8 GB" in why


# --------------------------------------------------------------------------
# backend selection
# --------------------------------------------------------------------------


def test_ollama_cannot_serve_an_offloaded_large_model():
    """The whole reason llama.cpp exists. Ollama has no expert offload, so a
    model that only fits with offload is simply unavailable there."""
    h = host(gpu_vram_gb=16.0, total_vram_gb=16.0, ram_gb=32.0)
    assert verdict(h, "chat-large", "ollama") == "unavailable"
    assert verdict(h, "chat-large", "llama.cpp") == "offload"


def test_backend_suggestion_flips_to_llama_on_a_small_card():
    """12 GB: llama.cpp, because it unlocks a large model Ollama cannot serve."""
    assert suggest_backend(host(gpu_vram_gb=12.0, ram_gb=32.0)) == "llama.cpp"


def test_backend_suggestion_stays_ollama_when_it_makes_no_difference():
    """24 GB holds a 30B outright, so offload buys nothing and Ollama is easier
    to operate. The suggestion must not push the more complex backend for nothing.
    """
    assert suggest_backend(host(gpu_vram_gb=24.0, ram_gb=32.0)) == "ollama"


def test_report_carries_its_backend():
    """Backend travels with the report.

    An earlier version threaded it through assess() and render() separately, and
    a caller desynced them — a verdict for one backend displayed under the
    other's name. Report makes that impossible.
    """
    h = host(gpu_vram_gb=12.0, ram_gb=32.0)
    r = report_for(h)
    assert r.backend == "llama.cpp"
    assert "llama.cpp" in r.render()


def test_report_json_round_trips():
    import json

    r = report_for(host(gpu_vram_gb=12.0))
    restored = json.loads(json.dumps(r.to_dict()))
    assert restored["backend"] == r.backend
    assert restored["host"]["total_vram_gb"] == 24.0 or restored["host"]["total_vram_gb"] == 12.0


# --------------------------------------------------------------------------
# hosts that cannot do the work
# --------------------------------------------------------------------------


def test_cuda_capabilities_are_unavailable_without_nvidia():
    """Image/voice/song need CUDA. On a host without it the honest answer is
    'unavailable', not 'slow' — puente ships no MPS or ROCm path."""
    h = host(gpu_vram_gb=0.0, total_vram_gb=0.0, gpu_count=0, has_nvidia_runtime=False)
    for name in ("image", "voice", "song", "image-video"):
        assert verdict(h, name) == "unavailable", name


def test_no_gpu_still_allows_chat_on_cpu_or_none():
    """Chat can in principle run on CPU, so it is not lumped in with the
    CUDA-only capabilities — but it should not be claimed as 'good' either."""
    h = host(gpu_vram_gb=0.0, total_vram_gb=0.0, gpu_count=0, has_nvidia_runtime=False)
    assert verdict(h, "chat") == "unavailable"
    assert "No NVIDIA GPU" in next(c.why for c in assess(h) if c.name == "chat")


def test_song_is_the_cheapest_capability():
    """ACE-Step at ~4.7 GB is the one capability that fits almost anywhere.
    Worth pinning, because it is the thing to offer a small-card user."""
    needs = {c.name: c.needs_gb for c in assess(host())}
    assert needs["song"] == min(v for v in needs.values() if v)


# --------------------------------------------------------------------------
# the DDR3 cliff
# --------------------------------------------------------------------------


def test_ddr3_gets_a_specific_warning_on_offload():
    """DDR3 is ~1.7x slower than DDR4 at streaming experts (ADR0010). That is a
    real caveat worth naming — but it must not change the verdict, since the
    capability still works."""
    fast = host(gpu_vram_gb=16.0, total_vram_gb=16.0, ram_gb=32.0, mem_class="ddr4")
    slow = host(gpu_vram_gb=16.0, total_vram_gb=16.0, ram_gb=32.0, mem_class="ddr3")
    assert verdict(slow, "image-video") == verdict(fast, "image-video")

    why = next(c.why for c in assess(slow) if c.name == "image-video")
    assert "DDR3" in why and "1.7x" in why


def test_unknown_memory_class_is_not_reported_as_good():
    """An undetected memory class must not silently read as fine."""
    h = host(gpu_vram_gb=16.0, total_vram_gb=16.0, ram_gb=32.0,
             mem_class="unknown", mem_bandwidth_gbs=None)
    why = next(c.why for c in assess(h) if c.name == "image-video")
    assert "DDR3" not in why  # no false alarm on an unread SPD


# --------------------------------------------------------------------------
# budget
# --------------------------------------------------------------------------


def test_budget_adds_ram_only_when_there_is_enough():
    """Below ~16 GB, treating RAM as model space would promise models that
    cannot actually be resident alongside everything else."""
    assert host(gpu_vram_gb=8.0, ram_gb=8.0).budget_gb == pytest.approx(8.0)
    assert host(gpu_vram_gb=8.0, ram_gb=32.0).budget_gb > 8.0


def test_two_cards_do_not_double_the_per_model_budget():
    """Two 24 GB cards can run two models, not one 48 GB model. The budget is a
    per-model figure, so it follows the largest card."""
    one = host(gpu_vram_gb=24.0, gpu_count=1, total_vram_gb=24.0)
    two = host(gpu_vram_gb=24.0, gpu_count=2, total_vram_gb=48.0)
    assert two.budget_gb == pytest.approx(one.budget_gb)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])