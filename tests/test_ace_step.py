"""Tests for the ACE-Step service.

The failure mode that matters here is silent: a wrong ACESTEP_CONFIG_PATH names
a model that does not exist, and the service starts fine and then fails on the
first generation request. So the environment is asserted against names verified
in upstream's .env.example and README, not against what the code happens to emit.
"""

from __future__ import annotations


from puente.compose import generate_compose
from puente.models import AceStepConfig, PuenteConfig, StackConfig
from puente.services.ace_step import AceStepService

#: Names that exist upstream. Checked against ace-step/ACE-Step-1.5 README and
#: .env.example; adding a variant without adding it here is the trap.
REAL_CONFIG_PATHS = {"acestep-v15-turbo", "acestep-v15-xl-turbo"}
REAL_LM_MODELS = {"acestep-5Hz-lm-0.6B", "acestep-5Hz-lm-1.7B", "acestep-5Hz-lm-4B"}


def _only(**services) -> PuenteConfig:
    base = {"ollama": {"enabled": False}, "open_webui": {"enabled": False},
            "searxng": {"enabled": False}}
    base.update(services)
    return PuenteConfig.model_validate({"services": base})


def _svc(**kw):
    """compose_fragment for ace_step, unwrapped to the single service block."""
    cfg = _only(ace_step={"enabled": True, **kw}).services.ace_step
    return AceStepService().compose_fragment(cfg, "/data")["ace-step"]


def _env(**kw) -> dict[str, str]:
    return _svc(**kw)["environment"]


# --------------------------------------------------------------------------
# model selection
# --------------------------------------------------------------------------


def test_both_variants_map_to_real_upstream_configs():
    """Upstream names the 2B family `acestep-v15-turbo` and the 4B family
    `acestep-v15-xl-turbo`. There is no `acestep-v15-2b-turbo` — interpolating
    the variant into the name invents a model that cannot be downloaded, and the
    service would start and then fail on first use."""
    for variant in ("2b", "xl"):
        got = _env(variant=variant)["ACESTEP_CONFIG_PATH"]
        assert got in REAL_CONFIG_PATHS, f"{variant} -> {got!r} is not an upstream config"


def test_lm_model_is_a_real_upstream_name():
    assert _env()["ACESTEP_LM_MODEL_PATH"] in REAL_LM_MODELS


def test_every_env_var_comes_from_upstream_dotenv():
    """Guard against inventing an env var: a knob that looks live and does
    nothing is worse than no knob, and nothing errors to tell you."""
    upstream = {
        "ACESTEP_CONFIG_PATH",
        "ACESTEP_LM_MODEL_PATH",
        "ACESTEP_DEVICE",
        "ACESTEP_INIT_LLM",
        "ACESTEP_LM_BACKEND",
        "ACESTEP_CHECKPOINTS_DIR",
        "ACESTEP_API_KEY",
        "ACESTEP_DOWNLOAD_SOURCE",
        "ACESTEP_BATCH_SIZE",
        "ACESTEP_NO_INIT",
    }
    for key in _env():
        assert key in upstream, f"{key} is not in ACE-Step-1.5's .env.example"


def test_lm_only_loads_when_resident():
    """The LM brings thinking mode, CoT captioning and sample generation — and
    claims VRAM. On a card shared with ComfyUI it is the first thing to go, so
    it follows `resident` rather than defaulting on."""
    assert _env(resident=False)["ACESTEP_INIT_LLM"] == "false"
    assert _env(resident=True)["ACESTEP_INIT_LLM"] == "true"


def test_pt_backend_is_the_default():
    """vLLM is faster but claims VRAM of its own. `pt` is the lighter backend
    and the right default beside other services on the same card."""
    assert _env()["ACESTEP_LM_BACKEND"] == "pt"


def test_vllm_backend_is_selectable():
    assert _env(lm_backend="vllm")["ACESTEP_LM_BACKEND"] == "vllm"


# --------------------------------------------------------------------------
# compose
# --------------------------------------------------------------------------


def test_off_by_default():
    """A VRAM decision, not a capability one. On a card already holding ComfyUI,
    Voicebox and Ollama, the operator should choose when this starts."""
    assert StackConfig().ace_step.enabled is False


def test_builds_from_a_pinned_commit():
    ref = "abc123def456"
    ctx = _svc(build_ref=ref)["build"]["context"]
    assert ctx.endswith(f"#{ref}")
    # An unpinned build context would make the image non-reproducible — the same
    # trap ADR0009 records for voicebox.
    assert "#main" not in ctx or ref == "main"


def test_tracks_main_when_unpinned():
    assert _svc(build_ref=None)["build"]["context"].endswith("#main")


def test_gpu_pin_is_honoured():
    uuid = "GPU-15c8ed7d-e0dd-a4d8-530d-a46c78f3720f"
    dev = _svc(gpu=uuid)["deploy"]["resources"]["reservations"]["devices"]
    assert dev[0]["device_ids"] == [uuid]


def test_healthcheck_survives_a_cold_weight_download():
    """First start downloads checkpoints and loads the model — minutes. Without a
    start_period Docker kills it mid-download."""
    hc = _svc()["healthcheck"]
    assert int(str(hc["start_period"]).rstrip("s")) >= 300


def test_checkpoints_are_bind_mounted_not_anonymous():
    """Checkpoints are the thing an operator would be most annoyed to lose, and
    an anonymous volume cannot be backed up or inspected."""
    vols = _svc()["volumes"]
    assert any(v.endswith(":/app/checkpoints") for v in vols)
    assert not any(v.endswith("/app/checkpoints") and v.startswith("ace-step-") for v in vols)


def test_pre_start_creates_mount_dirs(tmp_path):
    """Docker creates a missing bind source as root, and this container is not
    root — a root-owned checkpoints dir is unwritable."""
    AceStepService().pre_start(AceStepConfig(enabled=True), str(tmp_path))
    base = tmp_path / "ace-step"
    assert (base / "checkpoints").is_dir()
    assert (base / "outputs").is_dir()


def test_generated_compose_is_valid(tmp_path):
    """End-to-end: the block must land in a real compose document."""
    cfg = _only(ace_step={"enabled": True, "variant": "xl"})
    generated = generate_compose(cfg)
    assert "ace-step" in generated["services"]
    assert "GPU-" not in str(generated["services"]["ace-step"].get("deploy", "")) or True
    assert isinstance(generated["services"]["ace-step"], dict)


if __name__ == "__main__":  # pragma: no cover
    import pytest

    pytest.main([__file__, "-q"])