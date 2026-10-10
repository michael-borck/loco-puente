"""Demand-driven residency.

Which models should be in memory right now, decided by what people are
*actually doing* rather than by guessing at what they might ask next.

## Why observed demand rather than classification

The decision layer (`puente/decide.py`) answers "which capability does this
request want?". That is a different question from "what should stay loaded",
and the second one is better served by evidence than by prediction:

- **The evidence already exists.** Ollama knows which models are resident and
  when each expires. ComfyUI has a job queue. Caddy has access logs. Nothing has
  to be inferred.
- **Prediction is speculative.** A router that guesses correctly three turns
  early has saved nothing — it ran a model that was not being used. One that
  guesses wrong evicts the model somebody was about to use, and on a box with one
  card that is the whole cost.
- **It costs a dependency to be wrong.** Classification needs a model resident
  to make load decisions. Observing demand needs a log line.

So classification earns its place *upstream* — deciding which capability a
request wants, before anything is loaded — while residency is driven from
observed usage.

## What is actionable differs by backend, and that is the real constraint

`residency_plan` is deliberately backend-agnostic: it says *what* should be
resident, and each backend decides *how*.

| Backend | Evict mechanism | Cost of an eviction |
| --- | --- | --- |
| Ollama | per-request `keep_alive: 0` | ~none — the weights unload, the server stays up |
| llama.cpp | stop the container | a model reload is minutes |
| Containers (ComfyUI, Voicebox…) | stop the container | a model reload is minutes |

Ollama evicts cheaply because it already implements a residency TTL natively.
llama.cpp does not hot-swap models — one `llama-server` serves one GGUF — so its
load/unload is container lifecycle and therefore deliberately *sticky*. A policy
that thrashed it would be worse than no policy.

This is why `ResidencyPolicy` carries an `evict_cost`: something expensive to
evict should be evicted far less eagerly than something free to evict.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Literal

Action = Literal["keep", "load", "release"]


@dataclass
class Demand:
    """What one model-bearing thing has been doing."""

    name: str
    #: Minutes since it was last used. None = never used this window.
    idle_minutes: float | None = None
    #: Uses in the recent window. A service used repeatedly is "hot" even if the
    #: last use was a while ago, which matters for a service someone returns to
    #: all morning.
    recent_uses: int = 0
    #: What the backend would charge to evict and reload this. See the module
    #: docstring: Ollama ~0, llama.cpp/container minutes.
    evict_cost: Literal["free", "expensive"] = "expensive"

    @property
    def active(self) -> bool:
        """Used recently enough that releasing it would be felt."""
        return self.idle_minutes is not None and self.idle_minutes <= 15


@dataclass
class ResidencyPolicy:
    """Thresholds for the residency decision.

    Deliberately conservative, because an eviction that is wrong costs more than
    an eviction that is merely early: on a single-card box the model someone was
    about to use is gone, and reloading it takes minutes.
    """

    #: Release a model idle for longer than this.
    idle_release_minutes: float = 30.0
    #: Never release something used at least this many times recently, however
    #: long ago — a service people return to all session should not thrash.
    recent_use_protects: int = 3
    #: Only evict free-to-evict things this aggressively. Expensive ones wait for
    #: a much longer idle period.
    expensive_idle_release_minutes: float = 180.0

    def action_for(self, d: Demand) -> Action:
        if d.recent_uses >= self.recent_use_protects:
            return "keep"
        if d.idle_minutes is None:
            return "load" if d.recent_uses > 0 else "keep"

        limit = (
            self.idle_release_minutes
            if d.evict_cost == "free"
            else self.expensive_idle_release_minutes
        )
        if d.idle_minutes >= limit:
            return "release"
        return "keep"


@dataclass
class ResidencyPlan:
    """What to do, per item, and — importantly — why."""

    actions: dict[str, Action] = field(default_factory=dict)
    reasons: dict[str, str] = field(default_factory=dict)

    def releases(self) -> list[str]:
        return [n for n, a in self.actions.items() if a == "release"]

    def loads(self) -> list[str]:
        return [n for n, a in self.actions.items() if a == "load"]


def residency_plan(
    demand: list[Demand], policy: ResidencyPolicy | None = None
) -> ResidencyPlan:
    """Decide what should be resident.

    Pure and backend-agnostic: it takes observed demand and returns intent. The
    backend adapters turn that intent into an eviction, and are free to refuse —
    an adapter that cannot cheaply evict should decline rather than restart a
    container to satisfy the plan.
    """
    policy = policy or ResidencyPolicy()
    plan = ResidencyPlan()
    for d in demand:
        action = policy.action_for(d)
        plan.actions[d.name] = action
        plan.reasons[d.name] = _why(d, action, policy)
    return plan


def _why(d: Demand, action: Action, policy: ResidencyPolicy) -> str:
    if action == "keep" and d.recent_uses >= policy.recent_use_protects:
        return f"used {d.recent_uses}x recently — release would thrash"
    if action == "keep":
        idle = "never used" if d.idle_minutes is None else f"idle {d.idle_minutes:.0f}m"
        return f"{idle}, under the {policy.expensive_idle_release_minutes:.0f}m threshold"
    if action == "release":
        return (
            f"idle {d.idle_minutes:.0f}m — past the "
            f"{policy.idle_release_minutes if d.evict_cost == 'free' else policy.expensive_idle_release_minutes:.0f}m "
            f"threshold for a {d.evict_cost}-to-evict item"
        )
    return "in use"


# --------------------------------------------------------------------------
# observing demand
# --------------------------------------------------------------------------


def ollama_demand(
    base_url: str = "http://127.0.0.1:11434",
    timeout: float = 5.0,
    now: float | None = None,
) -> list[Demand]:
    """Read resident models from Ollama's `/api/ps` and convert to demand.

    The endpoint reports what is loaded and when it expires, which is the most
    direct evidence of demand available — Ollama is already tracking residency,
    so there is nothing to infer.

    Evict cost is `free` here: Ollama can drop weights without the server going
    away, which is exactly the asymmetry that makes a policy worth having.
    """
    import json
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(f"{base_url.rstrip('/')}/api/ps", timeout=timeout) as r:
            data = json.load(r)
    except (urllib.error.URLError, OSError, ValueError):
        # No Ollama, or not reachable. No demand to report is not an error.
        return []

    now = time.time() if now is None else now
    out: list[Demand] = []
    for m in data.get("models", []):
        # Ollama reports expires_at as an absolute unix time; "0" means it never
        # expires (resident until told otherwise).
        raw = m.get("expires_at") or 0
        idle = None
        try:
            if raw and float(raw) > 0:
                idle = max(0.0, (now - float(raw)) / 60.0)
        except (TypeError, ValueError):
            idle = None
        out.append(
            Demand(
                name=m.get("name") or m.get("model", "?"),
                idle_minutes=idle,
                recent_uses=1,  # resident implies it was used
                evict_cost="free",
            )
        )
    return out


def container_demand(
    service: str,
    container: str | None = None,
    idle_minutes: float | None = None,
) -> Demand:
    """Demand for a containerised service, where eviction means a restart.

    `evict_cost` is `expensive` because these reload model weights from disk, and
    for ComfyUI that is minutes. The policy treats them accordingly.
    """
    return Demand(
        name=service,
        idle_minutes=idle_minutes,
        recent_uses=1,
        evict_cost="expensive",
    )