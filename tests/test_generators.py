"""Smoke tests for the two generators that turn puente.yml into deployment artifacts.

These are the highest-leverage things to test in this project: `compose.py` and
`caddy.py` are pure functions from config to a docker-compose dict / a Caddyfile
string, and a silent regression in either produces a broken deployment rather
than a crash.

Two invariants carry most of the weight:

  * `generate_compose` skips services that are *disabled*.
  * `iter_proxied_services` does **not** — a declared `proxy:` block is served
    regardless of `enabled`. This asymmetry is deliberate (the user owns the
    proxy boundary) and is exactly why retiring chatterbox required setting
    `proxy: null`, not merely `enabled: false`. See the comment in puente.yml.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from puente.caddy import generate_caddyfile, iter_proxied_services
from puente.compose import generate_compose
from puente.models import PuenteConfig, ServiceConfig
from puente.services import ALL_SERVICES
from puente.services.caddy import CaddyService, _read_env_file

REPO_ROOT = Path(__file__).resolve().parent.parent


#: Services the schema turns on when puente.yml says nothing about them.
DEFAULT_ENABLED = ("ollama", "open_webui", "searxng")


def _config(**services) -> PuenteConfig:
    """Build a PuenteConfig from a partial services mapping (defaults preserved)."""
    return PuenteConfig.model_validate({"services": services})


def _only(**services) -> PuenteConfig:
    """Like `_config`, but first disables every default-on service.

    Lets a test assert on an exact service list without the schema's defaults
    leaking in. Explicit entries win over the disabling.
    """
    base = {name: {"enabled": False} for name in DEFAULT_ENABLED}
    base.update(services)
    return PuenteConfig.model_validate({"services": base})


# --------------------------------------------------------------------------
# The real puente.yml must stay loadable and must generate both artifacts.
# --------------------------------------------------------------------------


def test_repo_puente_yml_parses():
    raw = yaml.safe_load((REPO_ROOT / "puente.yml").read_text())
    config = PuenteConfig.model_validate(raw or {})
    assert config.services is not None


def test_repo_puente_yml_generates_both_artifacts():
    raw = yaml.safe_load((REPO_ROOT / "puente.yml").read_text())
    config = PuenteConfig.model_validate(raw or {})

    compose = generate_compose(config)
    assert "services" in compose and compose["services"], "no services generated"

    caddyfile = generate_caddyfile(config)
    assert "reverse_proxy" in caddyfile


# --------------------------------------------------------------------------
# compose: enabled / managed / install_method gating
# --------------------------------------------------------------------------


def test_compose_includes_enabled_docker_service():
    compose = generate_compose(_config(comfyui={"enabled": True}))
    assert "comfyui" in compose["services"]


def test_compose_skips_disabled_service():
    compose = generate_compose(
        _only(comfyui={"enabled": True}, swarmui={"enabled": False})
    )
    assert list(compose["services"]) == ["comfyui"]


def test_compose_skips_unmanaged_service():
    """`managed: false` means puente knows about it but does not run it.

    This is how the host-installed (systemd) Ollama is represented. Asserted in
    both directions so the test cannot pass vacuously.
    """
    managed = generate_compose(
        _config(ollama={"enabled": True, "managed": True, "install_method": "docker"})
    )
    assert "ollama" in managed["services"]

    unmanaged = generate_compose(
        _config(comfyui={"enabled": True}, ollama={"enabled": True, "managed": False})
    )
    assert "ollama" not in unmanaged["services"]


def test_default_enabled_services_are_exactly_these():
    """A bare config is not empty. Pinned because changing which services are on
    out of the box silently alters every fresh install."""
    config = PuenteConfig.model_validate({"services": {}})
    on = tuple(
        name
        for name in ALL_SERVICES
        if getattr(getattr(config.services, name, None), "enabled", False)
    )
    assert on == DEFAULT_ENABLED


def test_compose_empty_when_nothing_enabled():
    """With every default-on service explicitly disabled, no compose file is produced."""
    assert generate_compose(_only(comfyui={"enabled": False})) == {}


def test_compose_pins_gpu_to_requested_device():
    """`gpu: N` must reach the container as compose `device_ids: ["N"]`.

    Getting this wrong silently puts a workload on the wrong card — which on this
    box is the difference between a 24 GB 3090 and an 8 GB 2060 Super.
    """
    compose = generate_compose(_config(comfyui={"enabled": True, "gpu": 1}))
    dumped = yaml.safe_dump(compose["services"]["comfyui"])
    assert "device_ids" in dumped
    assert "'1'" in dumped or '"1"' in dumped or "- 1" in dumped


# --------------------------------------------------------------------------
# compose: swarmui → comfyui startup ordering (the "No backends available!" race)
# --------------------------------------------------------------------------


def test_comfyui_has_a_healthcheck():
    """swarmui gates its start on this; without it there is nothing to wait for."""
    compose = generate_compose(_config(comfyui={"enabled": True}))
    assert "healthcheck" in compose["services"]["comfyui"]


def test_swarmui_waits_for_comfyui_health_when_both_enabled():
    """When both are up, swarmui must depend on comfyui being *healthy* — else it
    probes a not-yet-loaded ComfyUI, latches the backend `errored`, and every
    request returns "No backends available!"."""
    compose = generate_compose(
        _config(comfyui={"enabled": True}, swarmui={"enabled": True})
    )
    deps = compose["services"]["swarmui"]["depends_on"]
    assert deps == {"comfyui": {"condition": "service_healthy"}}


def test_swarmui_depends_on_pruned_when_comfyui_disabled():
    """A dangling depends_on hard-errors `docker compose up`. If comfyui is off,
    the ordering constraint is moot and must be stripped, not emitted."""
    compose = generate_compose(
        _only(swarmui={"enabled": True}, comfyui={"enabled": False})
    )
    assert list(compose["services"]) == ["swarmui"]
    assert "depends_on" not in compose["services"]["swarmui"]


# --------------------------------------------------------------------------
# caddy: the enabled/proxy asymmetry — the chatterbox retirement gotcha
# --------------------------------------------------------------------------


def test_proxy_block_is_served_even_when_service_disabled():
    """A declared proxy block is served regardless of `enabled`.

    This is intentional. It is also the trap: disabling a service does NOT
    retire its public hostname.
    """
    config = _config(
        comfyui={
            "enabled": False,
            "proxy": {"host": "comfyui.example.org", "auth": "none"},
        }
    )
    hosts = [p.host for _, _, p in iter_proxied_services(config)]
    assert "comfyui.example.org" in hosts


def test_proxy_null_removes_the_route():
    """Setting `proxy: null` is what actually retires the route (cf. chatterbox)."""
    config = _config(comfyui={"enabled": False, "proxy": None})
    hosts = [p.host for _, _, p in iter_proxied_services(config)]
    assert hosts == []


def test_service_may_declare_several_hostnames():
    """voicebox splits into a basic-auth UI host and a bearer API host."""
    config = _config(
        voicebox={
            "enabled": True,
            "proxy": [
                {"host": "voice.example.org", "auth": "basic", "basic_group": "ui"},
                {"host": "voice-api.example.org", "auth": "bearer",
                 "token_env": "VOICE_TOKEN"},
            ],
        },
        caddy={"enabled": True, "users": {"ui": {"alice": "ALICE_PW"}}},
    )
    hosts = [p.host for _, _, p in iter_proxied_services(config)]
    assert hosts == ["voice.example.org", "voice-api.example.org"]


# --------------------------------------------------------------------------
# caddy: auth policy and secret handling
# --------------------------------------------------------------------------


def test_bearer_auth_emits_env_placeholder_not_the_token():
    """Secrets must never be baked into the Caddyfile — puente.yml stays committable."""
    config = _config(
        swarmui={
            "enabled": True,
            "proxy": {"host": "swarmui.example.org", "auth": "bearer",
                      "token_env": "SWARM_TOKEN"},
        },
        caddy={"enabled": True},
    )
    caddyfile = generate_caddyfile(config)
    assert "{$SWARM_TOKEN}" in caddyfile
    assert "respond @unauthorized 401" in caddyfile


def test_bearer_auth_accepts_a_list_of_token_envs():
    """Several env vars on one host = several valid keys, so a key can be
    rotated (add new, migrate clients, drop old) without a flag-day cutover."""
    config = _config(
        swarmui={
            "enabled": True,
            "proxy": {"host": "swarmui.example.org", "auth": "bearer",
                      "token_env": ["SWARM_TOKEN", "SWARM_TOKEN_2"]},
        },
        caddy={"enabled": True},
    )
    caddyfile = generate_caddyfile(config)
    # Repeating the field inside a matcher block is what OR-s the values. The
    # one-line form `header Authorization "A" "B"` is a Caddy parse error, and
    # a negated matcher would AND the negations and reject everything — so
    # pin the exact shape, not just the presence of both names.
    assert (
        '\t@authorized {\n'
        '\t\theader Authorization "Bearer {$SWARM_TOKEN}"\n'
        '\t\theader Authorization "Bearer {$SWARM_TOKEN_2}"\n'
        '\t}\n'
    ) in caddyfile
    # The upstream moves inside handle @authorized; an unguarded reverse_proxy
    # at site level would serve every request regardless of token.
    assert "\thandle @authorized {\n\t\treverse_proxy " in caddyfile
    assert "\t\trespond 401\n" in caddyfile


def test_bearer_token_env_list_reaches_the_env_file():
    """Every named token must be handed to the container, or the placeholder
    resolves empty and the host silently rejects a valid key."""
    config = _config(
        swarmui={
            "enabled": True,
            "proxy": {"host": "swarmui.example.org", "auth": "bearer",
                      "token_env": ["SWARM_TOKEN", "SWARM_TOKEN_2"]},
        },
        caddy={"enabled": True},
    )
    names = CaddyService()._secret_env_vars(config)
    assert "SWARM_TOKEN" in names and "SWARM_TOKEN_2" in names


def test_bearer_without_a_token_env_is_rejected():
    """An empty token_env used to render "Bearer {$}", locking out every client."""
    config = _config(
        swarmui={
            "enabled": True,
            "proxy": {"host": "swarmui.example.org", "auth": "bearer"},
        },
        caddy={"enabled": True},
    )
    with pytest.raises(ValueError, match="no token_env"):
        generate_caddyfile(config)


def test_basic_auth_emits_env_placeholder_not_the_hash():
    config = _config(
        comfyui={
            "enabled": True,
            "proxy": {"host": "image.example.org", "auth": "basic",
                      "basic_group": "ui"},
        },
        caddy={"enabled": True, "users": {"ui": {"alice": "ALICE_HASH"}}},
    )
    caddyfile = generate_caddyfile(config)
    assert "basic_auth {" in caddyfile
    assert "alice {$ALICE_HASH}" in caddyfile


def test_auth_none_adds_no_auth_directive():
    config = _config(
        open_webui={"enabled": True,
                    "proxy": {"host": "chat.example.org", "auth": "none"}},
        caddy={"enabled": True},
    )
    caddyfile = generate_caddyfile(config)
    assert "chat.example.org {" in caddyfile
    assert "basic_auth" not in caddyfile
    assert "respond @unauthorized" not in caddyfile


def test_basic_auth_with_no_resolvable_users_is_an_error():
    """Failing loudly beats generating a publicly-open host."""
    config = _config(
        comfyui={
            "enabled": True,
            "proxy": {"host": "image.example.org", "auth": "basic",
                      "basic_group": "nonexistent"},
        },
        caddy={"enabled": True, "users": {"ui": {"alice": "ALICE_HASH"}}},
    )
    with pytest.raises(ValueError, match="no users"):
        generate_caddyfile(config)


# --------------------------------------------------------------------------
# caddy pre_start: the .env is MERGED, never replaced
# --------------------------------------------------------------------------


def _pre_start_in(tmp_path: Path, monkeypatch, puente_yml: dict) -> Path:
    """Run CaddyService.pre_start against a throwaway puente.yml + data dir.

    `load_config()` resolves puente.yml relative to cwd, so chdir into the tmp
    dir to keep the real repo config out of these tests. Returns the .env path.
    """
    (tmp_path / "puente.yml").write_text(yaml.dump(puente_yml))
    monkeypatch.chdir(tmp_path)
    data = tmp_path / "data"
    (data / "caddy").mkdir(parents=True)
    return data / "caddy" / ".env"


_TWO_BEARER_HOSTS = {
    "services": {
        "caddy": {"enabled": True},
        "ollama": {
            "enabled": True,
            "proxy": {"host": "ollama.example.org", "auth": "bearer",
                      "token_env": "OLLAMA_TOKEN"},
        },
        "swarmui": {
            "enabled": True,
            "proxy": {"host": "swarmui.example.org", "auth": "bearer",
                      "token_env": "SWARMUI_TOKEN"},
        },
    }
}


def test_pre_start_keeps_secrets_it_cannot_resolve(tmp_path, monkeypatch):
    """The regression this merge exists for.

    Exporting only the NEW token used to rewrite .env with just that var and
    silently drop every other one — breaking auth on untouched hosts.
    """
    env_path = _pre_start_in(tmp_path, monkeypatch, _TWO_BEARER_HOSTS)
    env_path.write_text("OLLAMA_TOKEN=classkey\nSWARMUI_TOKEN=swarmkey\n")

    monkeypatch.delenv("OLLAMA_TOKEN", raising=False)
    monkeypatch.delenv("SWARMUI_TOKEN", raising=False)
    monkeypatch.setenv("SWARMUI_TOKEN", "rotated")

    CaddyService().pre_start(ServiceConfig(), str(tmp_path / "data"))

    written = _read_env_file(env_path)
    assert written["SWARMUI_TOKEN"] == "rotated"   # env wins
    assert written["OLLAMA_TOKEN"] == "classkey"   # carried forward, not lost


def test_pre_start_does_not_double_escape_on_repeat_runs(tmp_path, monkeypatch):
    """Carried-over values are already $$-escaped; re-escaping would corrupt
    bcrypt hashes a little more on every single `puente up`."""
    env_path = _pre_start_in(tmp_path, monkeypatch, _TWO_BEARER_HOSTS)
    monkeypatch.setenv("OLLAMA_TOKEN", "tok")
    monkeypatch.setenv("SWARMUI_TOKEN", "$2a$14$abc")

    data = str(tmp_path / "data")
    CaddyService().pre_start(ServiceConfig(), data)
    after_first = env_path.read_text()

    # Second run with nothing exported: values come from the file this time.
    monkeypatch.delenv("OLLAMA_TOKEN", raising=False)
    monkeypatch.delenv("SWARMUI_TOKEN", raising=False)
    CaddyService().pre_start(ServiceConfig(), data)

    assert env_path.read_text() == after_first
    assert _read_env_file(env_path)["SWARMUI_TOKEN"] == "$$2a$$14$$abc"


def test_pre_start_preserves_unrelated_keys(tmp_path, monkeypatch):
    """A secret for a host that's temporarily commented out of puente.yml (so
    _secret_env_vars never names it) must survive the merge."""
    env_path = _pre_start_in(tmp_path, monkeypatch, _TWO_BEARER_HOSTS)
    env_path.write_text("RETIRED_TOKEN=keepme\n")
    monkeypatch.setenv("OLLAMA_TOKEN", "tok")
    monkeypatch.setenv("SWARMUI_TOKEN", "tok2")

    CaddyService().pre_start(ServiceConfig(), str(tmp_path / "data"))

    assert _read_env_file(env_path)["RETIRED_TOKEN"] == "keepme"


def test_read_env_file_tolerates_comments_and_junk(tmp_path):
    path = tmp_path / ".env"
    path.write_text("# a comment\n\nA=1\nJUNKLINE\nB=x=y=z\n")
    assert _read_env_file(path) == {"A": "1", "B": "x=y=z"}
