"""Tests for `puente doctor` and config anchoring.

Two failure modes are pinned here, both of which produce a *wrong deployment*
rather than a crash:

  * **Anchoring.** `puente up` regenerates docker-compose.yml from whatever
    config it loaded. If that config isn't found, silently falling back to
    schema defaults rewrites a real stack's compose file with the three-service
    default. So `load_config(require=True)` must raise rather than default, and
    discovery must walk upward from the cwd.

  * **GPU pins.** A `gpu:` index that no longer matches real hardware either
    fails the compose file or lands the workload on the wrong card. Validating at
    generate time turns a confusing mid-deploy failure into a named message.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from puente.compose import generate_compose
from puente.doctor import (
    Check,
    check_gpu_pins,
    exit_code,
    report_dict,
    run_checks,
)
from puente.models import (
    CONFIG_ENV_VAR,
    ConfigNotFound,
    PuenteConfig,
    find_config_path,
    load_config,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def _only(**services) -> PuenteConfig:
    """A config with every default-on service disabled, so a test can assert
    an exact service list without schema defaults leaking in."""
    base = {"ollama": {"enabled": False}, "open_webui": {"enabled": False},
            "searxng": {"enabled": False}}
    base.update(services)
    return PuenteConfig.model_validate({"services": base})


# --------------------------------------------------------------------------
# config anchoring
# --------------------------------------------------------------------------


def test_config_discovery_walks_upward(tmp_path, monkeypatch):
    """Running `puente up` from a subdirectory must find the stack's config.

    Without this, every command invoked from anywhere but the stack root would
    act on defaults — which is the bug that made `puente up` from the wrong
    directory rewrite a production compose file.
    """
    (tmp_path / "puente.yml").write_text("services: {}\n")
    nested = tmp_path / "sub" / "deeper"
    nested.mkdir(parents=True)
    monkeypatch.chdir(nested)

    found = find_config_path()
    assert found is not None, "discovery did not walk up to the stack root"
    assert found.parent == tmp_path


def test_config_not_found_raises_when_required(tmp_path, monkeypatch):
    """`require=True` must raise instead of returning schema defaults.

    This is the guard that stops a defaults-fallback from overwriting a real
    stack's generated compose file.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)

    with pytest.raises(ConfigNotFound):
        load_config(require=True)


def test_config_not_found_defaults_when_not_required(tmp_path, monkeypatch):
    """Library callers (generate_compose etc.) still get defaults — only the CLI
    paths that write artifacts require a real file."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv(CONFIG_ENV_VAR, raising=False)

    config = load_config()
    assert config.services is not None


def test_config_env_var_pins_path(tmp_path, monkeypatch):
    """PUENTE_CONFIG is the escape hatch for cron/systemd, where the cwd is not
    the stack (ADR 0005's lab windows depend on this)."""
    pinned = tmp_path / "elsewhere" / "puente.yml"
    pinned.parent.mkdir(parents=True)
    pinned.write_text("services: {}\n")

    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.chdir(empty)
    monkeypatch.setenv(CONFIG_ENV_VAR, str(pinned))

    assert find_config_path() == pinned


def test_config_env_var_missing_file_is_not_found(tmp_path, monkeypatch):
    """A stale PUENTE_CONFIG must not silently fall back to a different file —
    that would reintroduce exactly the confusion the env var exists to remove."""
    monkeypatch.setenv(CONFIG_ENV_VAR, str(tmp_path / "nope.yml"))
    monkeypatch.chdir(tmp_path)
    assert find_config_path() is None


# --------------------------------------------------------------------------
# doctor: GPU pin validation
# --------------------------------------------------------------------------


class _FakeGPU:
    """Stand-in for gpu.GPU. Built on the real dataclass so it can't drift."""

    def __new__(cls, index: int, name: str, vram_gb: float, uuid: str = ""):
        from puente.gpu import GPU

        return GPU(
            index=index,
            uuid=uuid,
            name=name,
            vram_mb=int(vram_gb * 1024),
            driver="999.99",
            compute_cap="8.6",
        )

    def __init__(self, *args, **kwargs):
        pass

    def __str__(self):  # pragma: no cover - formatting only
        return self.name


GPU_A = "GPU-15c8ed7d-e0dd-a4d8-530d-a46c78f3720f"  # RTX 3090
GPU_B = "GPU-ce79654c-917a-e928-ad48-aca7c8014f47"  # RTX 4060 Ti


def test_gpu_pin_valid(monkeypatch):
    """A pin matching real hardware passes, and reports the inventory."""
    monkeypatch.setattr(
        "puente.gpu.detect_gpus", lambda: [_FakeGPU(0, "RTX 3090", 24.0, GPU_A)]
    )
    checks = check_gpu_pins(_only(comfyui={"enabled": True, "gpu": GPU_A}))
    assert [c.status for c in checks] == ["pass"]
    assert "RTX 3090" in checks[0].detail


def test_gpu_pin_rejects_unknown_device(monkeypatch):
    """A pin naming hardware that isn't present must fail loudly.

    Compose would otherwise reject it mid-deploy with an opaque runtime error,
    or — the failure this whole change exists to prevent — resolve it to a
    different card that happens to exist.
    """
    monkeypatch.setattr(
        "puente.gpu.detect_gpus", lambda: [_FakeGPU(0, "RTX 3090", 24.0, GPU_A)]
    )
    checks = check_gpu_pins(
        _only(comfyui={"enabled": True, "gpu": "GPU-deadbeef"})
    )
    assert checks[0].status == "fail"
    assert "GPU-deadbeef" in checks[0].detail
    assert checks[0].fix, "a failure must carry the command that fixes it"


def test_gpu_pin_without_hardware_fails(monkeypatch):
    """Pinning a GPU when none is detected is a config error, not a pass."""
    monkeypatch.setattr("puente.gpu.detect_gpus", lambda: [])
    checks = check_gpu_pins(_only(comfyui={"enabled": True, "gpu": GPU_A}))
    assert checks[0].status == "fail"


def test_no_gpu_pins_is_not_an_error(monkeypatch):
    """Services that don't pin a GPU are sharing all cards — legal, not a fault."""
    monkeypatch.setattr(
        "puente.gpu.detect_gpus", lambda: [_FakeGPU(0, "RTX 3090", 24.0, GPU_A)]
    )
    checks = check_gpu_pins(_only(comfyui={"enabled": True}))
    assert [c.status for c in checks] == ["pass"]


def test_gpu_pin_check_includes_ollama_instances(monkeypatch):
    """Ollama is configured through `instances`, not the generic service shape —
    its pins have to be validated too or the biggest workload goes unchecked."""
    monkeypatch.setattr(
        "puente.gpu.detect_gpus", lambda: [_FakeGPU(0, "RTX 3090", 24.0, GPU_A)]
    )
    config = PuenteConfig.model_validate(
        {
            "services": {
                "ollama": {
                    "enabled": True,
                    "instances": [
                        {"name": "primary", "gpu": "GPU-nope", "port": 11434}
                    ],
                }
            }
        }
    )
    checks = check_gpu_pins(config)
    assert checks[0].status == "fail"
    assert "ollama/primary" in checks[0].detail


# --------------------------------------------------------------------------
# GPU pin resolution: UUID vs index
# --------------------------------------------------------------------------


def test_resolve_gpu_accepts_uuid(monkeypatch):
    from puente.gpu import resolve_gpu

    gpus = [_FakeGPU(0, "RTX 3090", 24.0, GPU_A), _FakeGPU(1, "RTX 4060 Ti", 16.0, GPU_B)]
    assert resolve_gpu(GPU_A, gpus).index == 0
    assert resolve_gpu(GPU_B, gpus).index == 1


def test_resolve_gpu_accepts_bare_uuid_without_prefix(monkeypatch):
    """Tolerate the form people paste out of `nvidia-smi -L` output."""
    from puente.gpu import resolve_gpu

    gpus = [_FakeGPU(1, "RTX 4060 Ti", 16.0, GPU_B)]
    assert resolve_gpu(GPU_B.removeprefix("GPU-"), gpus).index == 1


def test_resolve_gpu_accepts_legacy_index(monkeypatch):
    """Existing configs pin integers; they must keep working."""
    from puente.gpu import resolve_gpu

    gpus = [_FakeGPU(0, "RTX 3090", 24.0, GPU_A), _FakeGPU(1, "RTX 4060 Ti", 16.0, GPU_B)]
    assert resolve_gpu(0, gpus).index == 0
    assert resolve_gpu("1", gpus).index == 1


def test_resolve_gpu_unknown_returns_none_not_a_fallback(monkeypatch):
    """An unknown pin must NOT resolve to some other GPU.

    Falling back to "any available card" here would silently reintroduce the
    wrong-card bug — the service would start on the wrong GPU and report no error.
    """
    from puente.gpu import resolve_gpu

    gpus = [_FakeGPU(0, "RTX 3090", 24.0, GPU_A)]
    assert resolve_gpu(7, gpus) is None
    assert resolve_gpu("GPU-deadbeef", gpus) is None


def test_resolve_gpu_does_not_confuse_uuid_for_index(monkeypatch):
    """A UUID must not be read as an integer index."""
    from puente.gpu import resolve_gpu

    gpus = [_FakeGPU(0, "RTX 3090", 24.0, GPU_A)]
    assert resolve_gpu(GPU_A, gpus).index == 0


def test_suggest_assignment_prefers_uuid(monkeypatch):
    """`puente init` must write UUIDs, so a fresh config is reorder-proof."""
    from puente.gpu import suggest_gpu_assignment

    gpus = [_FakeGPU(0, "RTX 3090", 24.0, GPU_A), _FakeGPU(1, "RTX 4060 Ti", 16.0, GPU_B)]
    out = suggest_gpu_assignment(gpus)
    # Bigger card wins the primary roles.
    assert out["primary_llm"] == GPU_A
    assert out["images"] == GPU_A
    assert out["voice"] == GPU_B


def test_suggest_assignment_falls_back_to_index_without_uuid():
    """A driver too old to report a UUID still gets a working pin."""
    from puente.gpu import suggest_gpu_assignment

    gpus = [_FakeGPU(0, "RTX 3090", 24.0, uuid="")]
    assert suggest_gpu_assignment(gpus)["primary_llm"] == "0"


def test_voicebox_pulls_published_image_and_keeps_build_fallback():
    """Both `image:` and `build:` are emitted, so compose pulls and only compiles
    if the pull fails. The build fallback is what makes an arm64 host or a
    missing tag survivable — losing it would strand those deployments."""
    from puente.compose import generate_compose

    compose = generate_compose(
        _only(
            voicebox={
                "enabled": True,
                "image": "ghcr.io/michael-borck/puente-voicebox:latest",
                "build_ref": "michael-borck/voicebox@4137a969bf110930ab563a74391517360a804554",
            }
        )
    )
    vb = compose["services"]["voicebox"]
    assert vb["image"] == "ghcr.io/michael-borck/puente-voicebox:latest"
    assert vb["build"]["context"].endswith("#4137a969bf110930ab563a74391517360a804554")


def test_voicebox_builds_from_source_when_no_image():
    """`image: null` forces a source build — the escape hatch for arm64 and for
    picking up a newer voicebox commit."""
    from puente.compose import generate_compose

    compose = generate_compose(
        _only(voicebox={"enabled": True, "image": None, "build_ref": None})
    )
    vb = compose["services"]["voicebox"]
    assert "image" not in vb
    assert vb["build"]["context"] == "https://github.com/jamiepine/voicebox.git"


def test_voicebox_idle_unload_only_with_a_fork():
    """The knob is only set when building from a fork that has the patch.

    Against upstream it would be a setting that looks live and silently does
    nothing — the exact failure the comment in voicebox.py warns about.
    """
    from puente.compose import generate_compose

    forked = generate_compose(
        _only(voicebox={"enabled": True, "build_ref": "michael-borck/voicebox@abc123"})
    )["services"]["voicebox"]
    upstream = generate_compose(
        _only(voicebox={"enabled": True, "build_ref": None})
    )["services"]["voicebox"]

    assert forked["environment"].get("VOICEBOX_IDLE_UNLOAD_SECONDS") == "600"
    assert "VOICEBOX_IDLE_UNLOAD_SECONDS" not in upstream["environment"]


def test_tutor_admin_does_not_pip_install_at_startup():
    """The container must not need PyPI access to boot.

    It used to run `pip install pymongo && python app.py` as its entrypoint,
    which meant a firewalled or air-gapped host could not start the service at
    all, the version was whatever upstream published that day, and a slow
    install was indistinguishable from a hung app.
    """
    from puente.compose import generate_compose

    ta = generate_compose(_only(tutor_admin={"enabled": True}))["services"]["tutor-admin"]
    command = " ".join(ta["command"])
    assert "pip install" not in command
    assert command == "python /data/app.py"


def test_tutor_admin_image_is_published_with_build_fallback():
    """Published image + local build fallback.

    The fallback matters more here than for the GPU services: this image builds
    in seconds (stdlib python + pymongo, no torch), so a missing tag is never a
    reason to be stuck.
    """
    from puente.compose import generate_compose

    ta = generate_compose(_only(tutor_admin={"enabled": True}))["services"]["tutor-admin"]
    assert ta["image"] == "ghcr.io/michael-borck/puente-tutor-admin:latest"
    assert ta["build"] == {"context": "./dockerfiles/tutor-admin"}


def test_tutor_admin_stays_on_loopback():
    """This app does no authentication of its own — Caddy does it.

    Publishing the port on 0.0.0.0 would expose unauthenticated account
    administration to the LAN, so the bind is asserted here.
    """
    from puente.compose import generate_compose

    ta = generate_compose(_only(tutor_admin={"enabled": True, "port": 8091}))[
        "services"
    ]["tutor-admin"]
    assert ta["ports"] == ["127.0.0.1:8091:8091"]


def test_tutor_admin_dockerfile_pins_pymongo():
    """The pin is the point. An unpinned dependency in an account-administration
    surface is a silent behaviour change on every rebuild."""
    import re
    from pathlib import Path

    dockerfile = Path(__file__).resolve().parent.parent / "puente" / "dockerfiles" / "tutor-admin" / "Dockerfile"
    text = dockerfile.read_text()
    pins = re.findall(r'pymongo==(\d+\.\d+\.\d+)', text)
    assert pins, "pymongo must be pinned with =="


def test_app_source_is_present_in_package_data():
    """`pre_start` reads app.py out of the installed package with no existence
    check, so a packaging miss turns into a bare FileNotFoundError at `up`."""
    from puente.services.tutor_admin import APP_SOURCE

    assert APP_SOURCE.is_file(), f"missing {APP_SOURCE}"


def test_voicebox_has_a_healthcheck_with_a_start_period():
    """Voicebox needs a healthcheck with a generous start_period.

    It loads TTS weights off disk, which takes minutes on a cold page cache.
    Without start_period, Docker starts counting a slow first response as a
    failed healthcheck and kills the container mid-load.
    """
    from puente.compose import generate_compose

    vb = generate_compose(_only(voicebox={"enabled": True}))["services"]["voicebox"]
    hc = vb["healthcheck"]
    assert "/health" in " ".join(hc["test"])
    assert int(str(hc["start_period"]).rstrip("s")) >= 120, (
        "start_period must cover a cold weight load"
    )


def test_voicebox_restart_is_backed_off():
    """`restart_delay` spaces the retries.

    Voicebox and ollama share the 16GB card, and at boot both load at once.
    Observed 2026-10-10: voicebox exited on cudaErrorDevicesUnavailable and
    plain `unless-stopped` restarted it immediately, so the log showed a
    shutdown and a health in the same minute — indistinguishable from nothing
    having happened.
    """
    from puente.compose import generate_compose

    vb = generate_compose(_only(voicebox={"enabled": True}))["services"]["voicebox"]
    assert vb["restart"] == "unless-stopped"
    assert int(str(vb["restart_delay"]).rstrip("s")) >= 15, "retries must back off"


# --------------------------------------------------------------------------
# network: overridable subnet / bridge
# --------------------------------------------------------------------------


def test_image_arch_flags_arm_host(monkeypatch):
    """An arm64 host cannot run these amd64-only images.

    The M3 Ultra in the Phase 2 roadmap is arm64. `docker pull` fails with a
    platform error that reads like a network problem, so it is caught here
    instead — with the source-build fallback named as the way out.
    """
    import puente.doctor as d

    monkeypatch.setattr(d.platform, "machine", lambda: "aarch64")
    check = d.check_image_arch(_only(comfyui={"enabled": True}))[0]
    assert check.status == "warn"
    assert "arm64" in check.detail or "aarch64" in check.detail
    assert "build:" in check.fix, "must name the source-build escape hatch"


def test_image_arch_passes_on_amd64(monkeypatch):
    import puente.doctor as d

    monkeypatch.setattr(d.platform, "machine", lambda: "x86_64")
    assert d.check_image_arch(_only(comfyui={"enabled": True}))[0].status == "pass"


def test_image_arch_skips_unrecognised_arch(monkeypatch):
    """Better to say nothing than to guess at an architecture we don't know."""
    import puente.doctor as d

    monkeypatch.setattr(d.platform, "machine", lambda: "riscv64")
    assert d.check_image_arch(_only(comfyui={"enabled": True}))[0].status == "skip"


def test_default_network_is_unchanged():
    """Existing deployments must generate byte-identical networking. Pinned
    because the UFW rule (`sudo ufw allow in on puente0`) and
    host.docker.internal resolution both depend on these exact values."""
    from puente.compose import resolve_network

    net = resolve_network(PuenteConfig())
    assert net == {
        "subnet": "172.28.0.0/24",
        "gateway": "172.28.0.1",
        "name": "puente0",
    }


def test_network_subnet_override_derives_gateway():
    """Setting only a subnet should be enough — the gateway is the first host
    address, derived rather than left stale from a different range."""
    from puente.compose import generate_compose, resolve_network

    cfg = PuenteConfig.model_validate({"network": {"subnet": "10.44.0.0/24"}})
    assert resolve_network(cfg)["gateway"] == "10.44.0.1"

    ipam = generate_compose(cfg)["networks"]["default"]["ipam"]["config"][0]
    assert ipam == {"subnet": "10.44.0.0/24", "gateway": "10.44.0.1"}


def test_network_gateway_outside_subnet_is_corrected():
    """A gateway from another range is worse than none: Docker accepts it, then
    the host can't route to its own containers. Derive instead."""
    from puente.compose import resolve_network

    cfg = PuenteConfig.model_validate(
        {"network": {"subnet": "10.44.0.0/24", "gateway": "192.168.99.1"}}
    )
    assert resolve_network(cfg)["gateway"] == "10.44.0.1"


def test_network_gateway_in_subnet_is_respected():
    """An explicit, coherent gateway is the operator's call — don't second-guess it."""
    from puente.compose import resolve_network

    cfg = PuenteConfig.model_validate(
        {"network": {"subnet": "10.44.0.0/24", "gateway": "10.44.0.99"}}
    )
    assert resolve_network(cfg)["gateway"] == "10.44.0.99"


def test_host_gateway_rewrite_follows_overridden_gateway():
    """`host.docker.internal` must point at the gateway actually in use.

    Hardcoding 172.28.0.1 here would break every service reaching a host
    service on a deployment that moved off the default range.
    """
    from puente.compose import generate_compose

    cfg = PuenteConfig.model_validate(
        {"services": {"caddy": {"enabled": True}}, "network": {"subnet": "10.44.0.0/24"}}
    )
    caddy = generate_compose(cfg)["services"]["caddy"]
    assert "host.docker.internal:10.44.0.1" in caddy["extra_hosts"]


# --------------------------------------------------------------------------
# portal: no foreign links
# --------------------------------------------------------------------------


def test_portal_falls_back_to_local_host_not_a_foreign_url():
    """The launcher page must never link to another deployment's hostname.

    A fresh install with no `proxy:` block used to link `chat.locopuente.org` —
    i.e. a student clicking Chat was sent to the PoC box.
    """
    from puente.portal import build_views

    config = PuenteConfig.model_validate(
        {
            "services": {
                "open_webui": {"enabled": True, "proxy": None},
                "ollama": {"enabled": True, "instances": [{"port": 11434}]},
            }
        }
    )
    urls = [
        svc.url for v in build_views(config, "10.0.0.5") for s in v.sections for svc in s.services
    ]
    assert urls, "expected at least the chat and ollama links"
    assert all("locopuente.org" not in u for u in urls), urls
    assert "http://10.0.0.5:3000" in urls


def test_portal_prefers_declared_proxy_block():
    """A declared `proxy:` block remains the single source of truth."""
    from puente.portal import build_views

    config = PuenteConfig.model_validate(
        {
            "services": {
                "open_webui": {
                    "enabled": True,
                    "proxy": {"host": "chat.example.org", "auth": "none"},
                }
            }
        }
    )
    urls = [
        svc.url for v in build_views(config, "10.0.0.5") for s in v.sections for svc in s.services
    ]
    assert "https://chat.example.org" in urls


# --------------------------------------------------------------------------
# doctor: contract
# --------------------------------------------------------------------------


def test_exit_code_only_fails_on_fail():
    """Warnings are advisory; only a hard failure should gate a pipeline."""
    assert exit_code([Check("a", "pass"), Check("b", "warn")]) == 0
    assert exit_code([Check("a", "pass"), Check("b", "fail")]) == 1


def test_report_dict_is_json_serialisable():
    """`--json` output has to survive a round trip for CI/monitoring consumers."""
    payload = report_dict([Check("a", "pass", "ok"), Check("b", "fail", "no", "fix it")])
    restored = json.loads(json.dumps(payload))
    assert restored["checks"][1]["fix"] == "fix it"
    assert restored["summary"]["fail"] == 1
    assert restored["exit_code"] == 1


def test_run_checks_is_read_only(tmp_path, monkeypatch):
    """The defining property of doctor: running it changes nothing on disk.

    A doctor that repairs as it goes is unsafe to run against a live box during
    an incident, which is exactly when it is most needed.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("puente.gpu.detect_gpus", lambda: [])
    (tmp_path / "puente.yml").write_text(yaml.dump({"services": {}}))
    config = load_config(require=True)

    before = {p.name for p in tmp_path.iterdir()}
    run_checks(config)
    assert {p.name for p in tmp_path.iterdir()} == before


def test_run_checks_returns_no_failures_on_this_host():
    """The PoC host should be self-consistent. Guards against checks that are
    trivially failing, or that misread a healthy host as broken."""
    checks = run_checks(load_config(path=REPO_ROOT / "puente.yml"))
    assert all(c.status != "fail" for c in checks), [
        (c.name, c.detail) for c in checks if c.status == "fail"
    ]


def test_network_subnet_ignores_own_bridge(monkeypatch):
    """A running stack holds its own pinned subnet by definition. Flagging that
    would make the check fail on every healthy live install."""
    monkeypatch.setattr(
        "puente.doctor._run",
        lambda cmd, timeout=10: (
            0,
            "172.28.0.0/24 dev puente0 proto kernel scope link src 172.28.0.1",
        ),
    )
    from puente.doctor import check_subnet

    assert check_subnet(PuenteConfig())[0].status == "pass"


def test_network_subnet_flags_foreign_route(monkeypatch):
    """A VPN or k8s claiming the range is a real conflict worth failing on."""
    monkeypatch.setattr(
        "puente.doctor._run",
        lambda cmd, timeout=10: (0, "172.28.0.0/24 dev tun0 proto kernel scope link"),
    )
    from puente.doctor import check_subnet

    check = check_subnet(PuenteConfig())[0]
    assert check.status == "fail"
    assert "tun0" in check.detail
    # The remediation must be actionable YAML, not "edit the source".
    assert "network:" in check.fix and "subnet:" in check.fix


def test_subnet_override_is_honoured_by_the_check(monkeypatch):
    """A host that moves the stack to a free range must be judged on THAT range,
    not on the built-in default."""
    monkeypatch.setattr("puente.doctor._run", lambda cmd, timeout=10: (0, ""))
    from puente.doctor import check_subnet

    cfg = PuenteConfig.model_validate({"network": {"subnet": "10.44.0.0/24"}})
    check = check_subnet(cfg)[0]
    assert check.status == "pass"
    assert "10.44.0.0/24" in check.detail


def test_up_warns_on_bad_gpu_pin_without_blocking(tmp_path, monkeypatch):
    """`puente up` reports a bad pin but still generates and starts.

    Advisory rather than fatal on purpose: `up` is frequently the first command
    run on a box whose driver is mid-repair, and refusing to start the whole
    stack over one bad pin would be a worse failure than reporting it.
    """
    from typer.testing import CliRunner

    from puente.cli import app

    monkeypatch.setattr(
        "puente.gpu.detect_gpus", lambda: [_FakeGPU(0, "RTX 3090", 24.0)]
    )
    # Don't actually touch docker. Stub subprocess.run globally (every module
    # shares the one `subprocess` module object) and record the calls.
    ran: list[tuple] = []

    class _Done:
        returncode = 0
        stdout = ""
        stderr = ""

    def _fake_run(*args, **kwargs):
        ran.append(args)
        return _Done()

    monkeypatch.setattr(subprocess, "run", _fake_run)

    # `up` needs a real config to act on, and must not write into the repo.
    stack = tmp_path / "stack"
    stack.mkdir()
    (stack / "puente.yml").write_text(
        yaml.dump(
            {
                "data_dir": str(tmp_path / "data"),
                "services": {"comfyui": {"enabled": True, "gpu": 3}},
            }
        )
    )
    monkeypatch.chdir(stack)

    result = CliRunner().invoke(app, ["up", "comfyui"])
    output = result.output

    assert "GPU pin problem" in output, output
    assert "gpu:3" in output
    # And it proceeded rather than aborting.
    assert any("docker" in str(call) for call in ran), "up did not reach docker"


# --------------------------------------------------------------------------
# regression: the real config must survive the doctor refactor
# --------------------------------------------------------------------------


def test_repo_config_still_generates_compose():
    """Anchoring changes touched config loading; the live stack must still build."""
    config = load_config(path=REPO_ROOT / "puente.yml")
    assert generate_compose(config)["services"]