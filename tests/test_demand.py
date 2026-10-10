"""Tests for the demand-driven residency policy.

The asymmetry between backends is the whole design. Ollama evicts weights for
free; a container has to reload them from disk, which is minutes. A policy that
treated them identically would either thrash containers or never release
anything, so `evict_cost` is load-bearing and pinned here.

Bias is deliberate and one-directional: an eviction that is wrong costs more
than one that is merely early, because on a single-card box the model somebody
was about to use is gone.
"""

from __future__ import annotations

import pytest

from puente.demand import (
    Demand,
    ResidencyPolicy,
    container_demand,
    residency_plan,
)


# --------------------------------------------------------------------------
# the asymmetry
# --------------------------------------------------------------------------


def test_free_to_evict_models_release_quickly():
    """Ollama drops weights without the server going away, so 30m idle is
    enough."""
    plan = residency_plan([Demand("gemma4", idle_minutes=45, evict_cost="free")])
    assert plan.actions["gemma4"] == "release"


def test_expensive_to_evict_waits_much_longer():
    """A container reloads from disk. Releasing at 45m would cost minutes every
    time someone returned to ComfyUI."""
    plan = residency_plan([Demand("comfyui", idle_minutes=45, evict_cost="expensive")])
    assert plan.actions["comfyui"] == "keep"

    later = residency_plan([Demand("comfyui", idle_minutes=200, evict_cost="expensive")])
    assert later.actions["comfyui"] == "release"


def test_expensive_threshold_is_much_larger():
    p = ResidencyPolicy()
    assert p.expensive_idle_release_minutes >= p.idle_release_minutes * 3


# --------------------------------------------------------------------------
# thrash protection
# --------------------------------------------------------------------------


def test_repeated_use_protects_regardless_of_idle_time():
    """A service people return to all session should not be released between
    visits, however long the individual gap was."""
    plan = residency_plan(
        [Demand("voicebox", idle_minutes=240, recent_uses=5, evict_cost="expensive")]
    )
    assert plan.actions["voicebox"] == "keep"
    assert "thrash" in plan.reasons["voicebox"]


def test_single_use_does_not_protect():
    plan = residency_plan([Demand("x", idle_minutes=240, recent_uses=1, evict_cost="free")])
    assert plan.actions["x"] == "release"


# --------------------------------------------------------------------------
# unknown state
# --------------------------------------------------------------------------


def test_never_used_is_not_released():
    """`idle_minutes is None` means we do not know, and destroying something on a
    guess is worse than leaving it."""
    plan = residency_plan([Demand("mystery", idle_minutes=None, recent_uses=0)])
    assert plan.actions["mystery"] == "keep"


def test_in_use_is_never_released():
    plan = residency_plan([Demand("busy", idle_minutes=0.0, evict_cost="free")])
    assert plan.actions["busy"] == "keep"


# --------------------------------------------------------------------------
# policy is a policy, not hardcoded behaviour
# --------------------------------------------------------------------------


def test_thresholds_are_configurable():
    """The default is deliberately conservative, but an operator on a card that
    cannot hold two models needs a shorter one."""
    aggressive = ResidencyPolicy(idle_release_minutes=5)
    plan = residency_plan([Demand("m", idle_minutes=10, evict_cost="free")], aggressive)
    assert plan.actions["m"] == "release"


def test_every_action_carries_a_reason():
    """A plan an operator cannot explain is one they will not trust to run
    unattended."""
    plan = residency_plan(
        [
            Demand("a", idle_minutes=1, evict_cost="free"),
            Demand("b", idle_minutes=200, evict_cost="free"),
        ]
    )
    for name in plan.actions:
        assert plan.reasons[name], f"{name} has no reason"


def test_plan_reports_what_it_would_change():
    plan = residency_plan(
        [
            Demand("hot", idle_minutes=2, evict_cost="free"),
            Demand("cold", idle_minutes=500, evict_cost="free"),
        ]
    )
    assert plan.releases() == ["cold"]
    assert plan.loads() == []


def test_empty_demand_is_an_empty_plan():
    plan = residency_plan([])
    assert plan.actions == {} and plan.releases() == []


# --------------------------------------------------------------------------
# adapters
# --------------------------------------------------------------------------


def test_container_demand_is_always_expensive_to_evict():
    """Getting this wrong would make a policy restart ComfyUI to satisfy a
    30-minute idle threshold."""
    assert container_demand("comfyui", idle_minutes=200).evict_cost == "expensive"


def test_ollama_demand_degrades_to_empty_when_unreachable():
    """Ollama may not be running, or may not be configured at all. No demand to
    report is not an error — it must not raise into whatever asked."""
    from puente.demand import ollama_demand

    assert ollama_demand(base_url="http://127.0.0.1:1") == []


def test_ollama_demand_reads_resident_models(monkeypatch):
    """`/api/ps` reports what is loaded and when it expires — the most direct
    evidence available, since Ollama is already tracking residency."""
    import json

    class _Resp:
        def read(self):
            return json.dumps(
                {
                    "models": [
                        {"name": "gemma4:12b", "expires_at": "2000000000"},
                        {"name": "qwen3.5:0.8b", "expires_at": "0"},
                    ]
                }
            ).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda *a, **k: _Resp())

    from puente.demand import ollama_demand

    got = ollama_demand(now=1_999_999_000.0)
    names = {d.name for d in got}
    assert names == {"gemma4:12b", "qwen3.5:0.8b"}
    # Ollama can drop weights without the server going away.
    assert all(d.evict_cost == "free" for d in got)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])