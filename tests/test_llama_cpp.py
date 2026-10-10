"""Tests for the llama.cpp backend.

The flag construction is the whole point of this backend, and a wrong flag fails
*silently*: `-ncmoe 24` on a dense model is accepted and does nothing, and an
`-ngl` that is too high simply gets clamped. So the argv is asserted exactly,
rather than smoke-tested.
"""

from __future__ import annotations

import pytest

from puente.compose import generate_compose
from puente.models import LlamaCppInstance, PuenteConfig
from puente.services.llama_cpp import LlamaCppService, build_command


def _only(**services) -> PuenteConfig:
    base = {"ollama": {"enabled": False}, "open_webui": {"enabled": False},
            "searxng": {"enabled": False}}
    base.update(services)
    return PuenteConfig.model_validate({"services": base})


def _svc(**kw):
    """compose_fragment for a llama_cpp block — the service gets its own config,
    not the whole PuenteConfig."""
    cfg = _only(llama_cpp={"enabled": True, **kw}).services.llama_cpp
    return LlamaCppService().compose_fragment(cfg, "/data")


# --------------------------------------------------------------------------
# argv
# --------------------------------------------------------------------------


def test_full_gpu_offload_by_default():
    """A model that fits should use the whole card."""
    cmd = build_command(LlamaCppInstance(model="m.gguf"), 8081)
    assert "-ngl" in cmd
    assert cmd[cmd.index("-ngl") + 1] == "999"


def test_n_gpu_layers_bounds_the_card():
    """`n_gpu_layers: 12` is the explicit way to leave VRAM for another service."""
    cmd = build_command(LlamaCppInstance(model="m.gguf", n_gpu_layers=12), 8081)
    assert cmd[cmd.index("-ngl") + 1] == "12"


def test_cpu_moe_offloads_experts_to_ram():
    """The reason this backend exists.

    `-ncmoe N` keeps the routed experts of the first N layers in system RAM
    while attention, KV and shared experts stay on the GPU. On a card shared
    with image/voice/song services this is what makes a large MoE model
    coexist rather than thrash.
    """
    cmd = build_command(LlamaCppInstance(model="m.gguf", cpu_moe=24), 8081)
    assert "-ncmoe" in cmd
    assert cmd[cmd.index("-ncmoe") + 1] == "24"


def test_cpu_moe_all_uses_999():
    cmd = build_command(LlamaCppInstance(model="m.gguf", cpu_moe="all"), 8081)
    assert cmd[cmd.index("-ncmoe") + 1] == "999"


def test_no_cpu_moe_flag_when_unset():
    """A dense model must not carry the flag — it is a no-op there, and a flag
    that looks live but does nothing is worse than no flag."""
    cmd = build_command(LlamaCppInstance(model="m.gguf"), 8081)
    assert "-ncmoe" not in cmd
    assert "--cpu-moe" not in cmd


def test_gguf_suffix_added_but_not_doubled():
    """People habitually omit .gguf; double-appending it would fail to load."""
    assert build_command(LlamaCppInstance(model="m"), 8081)[1] == "/models/m.gguf"
    assert build_command(LlamaCppInstance(model="m.gguf"), 8081)[1] == "/models/m.gguf"


def test_hf_file_wins_over_model():
    cmd = build_command(
        LlamaCppInstance(model="ignored", hf_file="repo/model-Q4.gguf"), 8081
    )
    assert cmd[1] == "/models/repo/model-Q4.gguf"


def test_disable_thinking_sets_zero_budget():
    """Classroom Q&A: the thinking pass cost ~5x latency for no measurable gain."""
    cmd = build_command(LlamaCppInstance(model="m", disable_thinking=True), 8081)
    assert cmd[cmd.index("--reasoning-budget") + 1] == "0"


def test_alias_and_extra_args_pass_through():
    cmd = build_command(
        LlamaCppInstance(model="m", alias="chat", extra_args=["-fa", "on"]), 8081
    )
    assert cmd[cmd.index("-a") + 1] == "chat"
    assert cmd[-2:] == ["-fa", "on"]


def test_ctx_and_parallel_reach_the_server():
    cmd = build_command(LlamaCppInstance(model="m", ctx=32768, parallel=2), 8081)
    assert cmd[cmd.index("-c") + 1] == "32768"
    assert cmd[cmd.index("-np") + 1] == "2"


# --------------------------------------------------------------------------
# compose
# --------------------------------------------------------------------------


def test_one_container_per_instance_on_its_own_port():
    """llama-server serves one model per process, so several models means
    several instances."""
    frags = _svc(instances=[
        {"name": "chat", "model": "a.gguf", "port": 8081},
        {"name": "code", "model": "b.gguf", "port": 8082},
    ])
    assert set(frags) == {"llama-cpp-chat", "llama-cpp-code"}
    assert frags["llama-cpp-chat"]["ports"] == ["8081:8081"]
    assert frags["llama-cpp-code"]["ports"] == ["8082:8082"]
    assert frags["llama-cpp-chat"]["container_name"] == "puente-llama-cpp-chat"


def test_no_instances_emits_nothing():
    assert _svc(instances=[]) is None


def test_instance_names_are_slugged_for_compose():
    frags = _svc(instances=[{"name": "Big Model", "model": "a.gguf"}])
    assert "llama-cpp-big-model" in frags


def test_models_mounted_read_only():
    """The models directory is operator-owned. A container that can write it can
    replace the model, and the next start would silently serve something else."""
    frags = _svc(instances=[{"name": "a", "model": "m.gguf"}])
    mount = [v for v in frags["llama-cpp-a"]["volumes"] if v.endswith(":/models:ro")]
    assert mount, "models must be mounted read-only"


def test_gpu_pin_reaches_each_instance():
    uuid = "GPU-15c8ed7d-e0dd-a4d8-530d-a46c78f3720f"
    frags = _svc(instances=[
        {"name": "a", "model": "m.gguf", "gpu": uuid},
        {"name": "b", "model": "m.gguf"},
    ])
    pinned = frags["llama-cpp-a"]["deploy"]["resources"]["reservations"]["devices"]
    assert pinned[0]["device_ids"] == [uuid]
    # Unpinned means NO deploy block — every card, not none.
    assert "deploy" not in frags["llama-cpp-b"]


def test_healthcheck_has_a_generous_start_period():
    """Loading a large GGUF off disk takes minutes cold; without start_period
    Docker kills it mid-load."""
    frags = _svc(instances=[{"name": "a", "model": "m.gguf"}])
    hc = frags["llama-cpp-a"]["healthcheck"]
    assert int(str(hc["start_period"]).rstrip("s")) >= 300


def test_named_hf_volumes_are_declared():
    """Compose rejects a named volume a service references but nothing declares."""
    cfg = _only(llama_cpp={"enabled": True,
                           "instances": [{"name": "a", "model": "m.gguf"}]})
    generated = generate_compose(cfg)
    assert "llama-cpp-a-hf" in generated["volumes"]


def test_disabled_by_default():
    """Enabling both backends at once would have two servers contending for the
    same card, so this stays opt-in until it is proven."""
    from puente.models import StackConfig

    assert StackConfig().llama_cpp.enabled is False


def test_pre_start_warns_when_the_gguf_is_missing(tmp_path):
    """llama-server starts fine with a missing model and only fails on the first
    request — a confusing way to learn a file is absent."""
    from puente.models import LlamaCppConfig

    cfg = LlamaCppConfig(enabled=True, instances=[LlamaCppInstance(model="absent")])
    LlamaCppService().pre_start(cfg, str(tmp_path))
    models = tmp_path / "llama.cpp" / "models"
    assert models.is_dir(), "models dir must be created"


def test_pre_start_silent_when_the_gguf_is_present(tmp_path, capsys):
    from puente.models import LlamaCppConfig

    models = tmp_path / "llama.cpp" / "models"
    models.mkdir(parents=True)
    (models / "present.gguf").write_bytes(b"x")
    cfg = LlamaCppConfig(enabled=True, instances=[LlamaCppInstance(model="present")])
    LlamaCppService().pre_start(cfg, str(tmp_path))
    assert "absent" not in capsys.readouterr().out


def test_doctor_sees_llama_cpp_pins(monkeypatch):
    """The pins live inside instances, so the generic requires_gpu scan misses
    them — the same class of gap that let an invalid pin through before."""
    from puente.doctor import check_gpu_pins

    class _G:
        index, name, vram_gb = 0, "RTX 3090", 24.0
        uuid = "GPU-15c8ed7d-e0dd-a4d8-530d-a46c78f3720f"

        def short_uuid(self):
            return self.uuid

    monkeypatch.setattr("puente.gpu.detect_gpus", lambda: [_G()])
    cfg = _only(llama_cpp={"enabled": True, "instances": [
        {"name": "chat", "model": "m.gguf", "gpu": "GPU-nope"}
    ]})
    checks = check_gpu_pins(cfg)
    assert checks[0].status == "fail"
    assert "llama_cpp/chat" in checks[0].detail


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])