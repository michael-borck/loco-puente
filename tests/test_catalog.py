"""Tests for the service catalog and the LocalAI backend.

Both were added in ADR0012, and both exist to *remove* code rather than add it:
the catalog replaces hand-written service classes with declarations, and LocalAI
replaces a capability Puente was about to build twice.

The invariants worth pinning here are the ones whose failure is silent. A
generated service that emits a subtly wrong compose fragment produces a broken
deployment rather than a crash, and an image with a floating tag means a
`puente up` six months from now runs code nobody tested.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from puente.catalog import (
    BUNDLED_CATALOG_DIR,
    PROFILES,
    CatalogEntry,
    _service_class,
    entries_for_profile,
    load_entries,
)
from puente.compose import generate_compose
from puente.decide import LocalAIBackend, Question, Option, route
from puente.models import LocalAIConfig, PuenteConfig
from puente.services import ALL_SERVICES
from puente.services.localai import LocalAIService, build_command


def _config(**services) -> PuenteConfig:
    return PuenteConfig.model_validate({"services": services})


# --------------------------------------------------------------------------
# the bundled catalog must load and be well-formed
# --------------------------------------------------------------------------


def test_bundled_catalog_loads():
    entries = load_entries()
    assert entries, "the bundled catalog is empty — the package data is missing"


def test_every_catalog_entry_is_a_registered_service():
    """A declared service that never becomes a ServiceBase is invisible to
    compose, the portal and the CLI — the declaration would be a no-op."""
    entries = load_entries()
    missing = {e.id for e in entries.values()} - set(ALL_SERVICES)
    assert not missing, f"catalog entries with no service class: {missing}"


def test_every_catalog_image_is_pinned():
    """No floating tags on third-party images.

    `latest` means the stack is not reproducible and `puente doctor` cannot say
    what someone is actually running.

    Exempt: images puente publishes itself. Those are rebuilt from a pinned
    commit (ADR0009), so the tag is a delivery detail rather than an upstream
    pin — the commit is the pin.
    """
    for entry in load_entries().values():
        tag = entry.image.rsplit("/", 1)[-1]
        assert ":" in tag, f"{entry.id}: image {entry.image!r} has no tag"
        if entry.puente_published:
            continue
        assert not tag.endswith(":latest"), (
            f"{entry.id}: image {entry.image!r} uses a floating tag"
        )


def test_catalog_rejects_an_unpinned_image():
    with pytest.raises(ValueError, match="no tag"):
        CatalogEntry(
            id="x",
            name="X",
            description="",
            image="docker.io/library/x",
            container_port=80,
        )


def test_catalog_entry_ids_are_valid_keys():
    """An id with a dash or dot in it would break the config key and the compose
    service name in different ways."""
    with pytest.raises(ValueError):
        CatalogEntry(
            id="bad-id",
            name="Bad",
            description="",
            image="docker.io/library/x:1",
            container_port=80,
        )


def test_tier3_provides_and_hardware_metadata():
    """The point of the catalog: honest hardware fit without running anything.

    Every one of these is CPU-only, and saying so wrongly would offer a service
    on a box that cannot run it (ADR0001's reason for asking rather than
    guessing).
    """
    entries = load_entries()
    for entry in entries.values():
        assert entry.needs_vram_mb == 0, (
            f"{entry.id} declares VRAM but has no catalog-side GPU work; either "
            f"it is CPU-only or it belongs in a hand-written service"
        )
        assert entry.provides, f"{entry.id} declares no capability"


# --------------------------------------------------------------------------
# generated services behave like hand-written ones
# --------------------------------------------------------------------------


def test_generated_service_emits_a_compose_fragment():
    config = _config(stirling_pdf={"enabled": True})
    compose = generate_compose(config)
    svc = compose["services"]["stirling-pdf"]
    assert svc["image"] == "docker.io/stirlingtools/stirling-pdf:2"
    assert svc["ports"] == ["8089:8080"]
    assert svc["container_name"] == "puente-stirling-pdf"


def test_generated_service_resolves_templates():
    """`{data_dir}` and `{port}` must both expand — the volume is what makes
    notebooks survive a container recreate."""
    config = _config(jupyter={"enabled": True})
    svc = generate_compose(config)["services"]["jupyter"]
    assert any(
        v.startswith("/") and "{data_dir}" not in v for v in svc["volumes"]
    ), svc["volumes"]
    assert svc["ports"][0] == "8899:8888"


def test_generated_service_env_is_overridable_from_config():
    """Catalog env is a *default*. The operator's puente.yml wins — otherwise a
    secret could never be set without editing the installed package."""
    config = _config(
        jupyter={"enabled": True, "environment": {"JUPYTER_TOKEN": "s3cret"}}
    )
    svc = generate_compose(config)["services"]["jupyter"]
    assert svc["environment"]["JUPYTER_TOKEN"] == "s3cret"


def test_generated_service_is_absent_when_disabled():
    """Tier 3 is opt-in. A catalog entry enabled by default would put a notebook
    server on every fresh install, which is the exact thing ADR0012 rejects."""
    compose = generate_compose(
        _config(ollama={"enabled": False}, open_webui={"enabled": False},
                searxng={"enabled": False})
    )
    assert "jupyter" not in compose.get("services", {})
    assert "stirling-pdf" not in compose.get("services", {})


def test_generated_service_class_name_is_readable():
    """`__name__` shows up in tracebacks and CLI errors, so 'CatalogService'
    alone would make a failure much harder to trace to an entry."""
    entry = load_entries()["jupyter"]
    assert _service_class(entry).__name__ == "JupyterCatalogService"


def test_builtin_catalog_entries_keep_their_handwritten_class():
    """`implementation: builtin` means the class is the reason — the generated
    one must not silently win and drop the lifecycle logic."""
    from puente.services.anythingllm import AnythingLLMService
    from puente.services.searxng import SearXNGService

    assert ALL_SERVICES["anythingllm"] is AnythingLLMService
    assert ALL_SERVICES["searxng"] is SearXNGService


# --------------------------------------------------------------------------
# profiles
# --------------------------------------------------------------------------


def test_profiles_only_name_real_entries():
    known = set(load_entries())
    for profile, ids in PROFILES.items():
        unknown = set(ids) - known
        assert not unknown, f"profile {profile} names unknown entries: {unknown}"


def test_unknown_profile_raises():
    """A typo must fail loudly. Silently enabling nothing is the worst outcome
    for `puente enable @offce`."""
    with pytest.raises(KeyError):
        entries_for_profile("offce")


def test_office_profile_is_the_three_cpu_tools():
    ids = {e.id for e in entries_for_profile("office")}
    assert ids == {"stirling_pdf", "excalidraw", "jupyter"}


#: Catalog entries allowed to be on by default. SearXNG predates the catalog,
#: is one of the three services `puente init` enables, and Open Web UI's web
#: search points at it — ADR0012 records the exemption rather than breaking
#: web search on every existing install.
DEFAULT_ON_CATALOG = {"searxng"}


def test_every_tier3_entry_is_opt_in():
    """Nothing in the catalog may become default-on — pinned by ADR0012."""
    for entry in load_entries().values():
        cfg = getattr(
            PuenteConfig.model_validate({"services": {}}).services, entry.id, None
        )
        assert cfg is not None, f"{entry.id} has no config block"
        if entry.id in DEFAULT_ON_CATALOG:
            continue
        assert not cfg.enabled, f"{entry.id} is enabled by default; ADR0012 forbids it"


def test_the_default_on_exemption_is_still_explicit():
    """The exemption must stay a short list, not become a way to opt anything
    in. Adding to it should be a deliberate edit with a reason."""
    assert DEFAULT_ON_CATALOG <= set(load_entries())


# --------------------------------------------------------------------------
# user catalog overlay
# --------------------------------------------------------------------------


def test_user_catalog_overrides_a_bundled_entry(tmp_path: Path):
    """Re-pinning a catalogued image is the single most likely thing an operator
    will want, and must not require editing an installed package."""
    (tmp_path / "catalog").mkdir()
    (tmp_path / "catalog" / "mine.yml").write_text(
        "services:\n"
        "  - id: jupyter\n"
        "    name: JupyterLab\n"
        "    description: pinned locally\n"
        "    image: docker.io/jupyter/minimal-notebook:2026-01\n"
        "    container_port: 8888\n"
        "    provides: [notebooks]\n"
    )
    entries = load_entries(tmp_path)
    assert entries["jupyter"].image.endswith(":2026-01")
    assert entries["jupyter"].description == "pinned locally"


def test_user_catalog_can_add_an_unknown_service(tmp_path: Path):
    (tmp_path / "catalog").mkdir()
    (tmp_path / "catalog" / "mine.yml").write_text(
        "services:\n"
        "  - id: my_tool\n"
        "    name: My Tool\n"
        "    description: something puente has never heard of\n"
        "    image: docker.io/example/mytool:1.0\n"
        "    container_port: 8000\n"
        "    provides: [custom]\n"
    )
    assert "my_tool" in load_entries(tmp_path)


def test_malformed_catalog_raises(tmp_path: Path):
    """Never skip a bad file. A silently missing service is unexplainable to an
    operator who just asked for it."""
    (tmp_path / "catalog").mkdir()
    (tmp_path / "catalog" / "bad.yml").write_text(
        "services:\n  - id: x\n    name: X\n"  # no image
    )
    with pytest.raises(Exception):
        load_entries(tmp_path)


def test_catalog_ships_with_the_package():
    """package-data in pyproject must actually include it, or an installed
    puente silently loses the office profile."""
    assert BUNDLED_CATALOG_DIR.is_dir()
    assert list(BUNDLED_CATALOG_DIR.glob("*.yml"))


# --------------------------------------------------------------------------
# LocalAI backend
# --------------------------------------------------------------------------


def test_localai_is_off_by_default():
    """Two inference servers on one card is the failure this avoids."""
    assert not PuenteConfig.model_validate({"services": {}}).services.localai.enabled


def test_localai_compose_fragment():
    """Port 8080 matches LocalAI's own default, so it agrees with everything
    written about it upstream."""
    svc = generate_compose(
        _config(ollama={"enabled": False}, localai={"enabled": True})
    )["services"]["localai"]
    assert svc["ports"] == ["8080:8080"]
    assert svc["volumes"] == ["localai-models:/models"]
    assert svc["restart"] == "unless-stopped"


def test_localai_adopts_an_existing_model_library():
    """Someone with 211 GB of GGUFs on disk should not be told to re-download
    them — same reasoning as Ollama's models-dir adoption."""
    svc = generate_compose(
        _config(ollama={"enabled": False},
                localai={"enabled": True, "models_dir": "/mnt/models"})
    )["services"]["localai"]
    assert svc["volumes"] == ["/mnt/models:/models"]


def test_localai_exposes_cuda_env():
    """The nvidia runtime env, not a `deploy:` block — `deploy.resources` only
    applies under swarm, and this stack runs plain `docker compose up`."""
    svc = generate_compose(
        _config(ollama={"enabled": False},
                localai={"enabled": True, "gpu": "GPU-abc123"})
    )["services"]["localai"]
    assert svc["environment"]["CUDA_VISIBLE_DEVICES"] == "GPU-abc123"


def test_localai_command_is_a_pure_function():
    args = build_command(LocalAIConfig(context_size=4096, parallel=2))
    assert "--context-size" in args and "4096" in args
    assert "--parallel" in args and "2" in args
    assert "--preload-backend" in args
    # A flag that is not requested must not appear.
    assert "--debug" not in args


def test_localai_debug_flag_only_when_asked():
    assert "--debug" in build_command(LocalAIConfig(debug=True))
    assert "--debug" not in build_command(LocalAIConfig(debug=False))


def test_localai_native_install_emits_nothing():
    svc = LocalAIService()
    cfg = LocalAIConfig(enabled=True, install_method="native")
    assert svc.compose_fragment(cfg, "/tmp") is None


# --------------------------------------------------------------------------
# LocalAI decision backend
# --------------------------------------------------------------------------


_Q = Question(
    name="capability",
    instructions="Which capability?",
    options=(
        Option("chat", "conversation"),
        Option("image", "picture"),
        Option("other", ""),
    ),
)


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        import json

        return json.dumps(self._payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_localai_backend_reads_a_choice(monkeypatch):
    backend = LocalAIBackend()
    monkeypatch.setattr(
        "puente.decide.urllib.request.urlopen",
        lambda *a, **k: _FakeResponse({"choice": "image", "confidence": 0.9}),
    )
    answer = backend.answer("draw a fox", _Q)
    assert answer.choice == "image"
    assert answer.confidence == 0.9
    assert answer.backend == "localai"


def test_localai_backend_degrades_when_the_engine_is_down(monkeypatch):
    """A routing decision must never be the thing that breaks a request."""
    def _boom(*a, **k):
        raise OSError("connection refused")

    monkeypatch.setattr("puente.decide.urllib.request.urlopen", _boom)
    backend = LocalAIBackend()
    answer = backend.answer("draw a fox", _Q)
    assert answer.confidence == 0.0
    assert answer.backend.endswith(":error")
    # And so the threshold declines rather than acting on a coin flip.
    r = route("draw a picture of a red fox", backend=backend)
    assert not r.decided


def test_localai_backend_degrades_on_a_shape_it_does_not_recognise(monkeypatch):
    """The newest upstream surface; an unexpected response must decline, never
    guess."""
    monkeypatch.setattr(
        "puente.decide.urllib.request.urlopen",
        lambda *a, **k: _FakeResponse({"something": "else"}),
    )
    answer = LocalAIBackend().answer("draw a fox", _Q)
    assert answer.confidence == 0.0


def test_localai_backend_takes_the_argmax_when_no_label_is_returned(monkeypatch):
    monkeypatch.setattr(
        "puente.decide.urllib.request.urlopen",
        lambda *a, **k: _FakeResponse({"probabilities": {"chat": 0.1, "image": 0.7}}),
    )
    answer = LocalAIBackend().answer("draw a fox", _Q)
    assert answer.choice == "image"
    assert answer.confidence == pytest.approx(0.7)


# --------------------------------------------------------------------------
# routing follows the enabled engine
# --------------------------------------------------------------------------

#: Requests with a clear lexical signal, so these tests exercise the *service
#: resolution* and not the fallback's ability to find a capability at all. A
#: request like "hello there" declines with no signal, which is correct behaviour
#: and would test nothing here.
_CHAT = "let's chat about this essay"
_CODE = "write a python function to reverse a list"
_SEARCH = "search the web for recent news"


def test_routes_point_at_the_enabled_engine():
    """A route to a service the operator just switched off is the one failure
    this layer cannot recover from."""
    r = route(_CODE, localai_enabled=True)
    assert r.decided, r.reason
    assert r.service == "localai"


def test_routes_default_to_the_static_map():
    assert route(_CODE).service == "ollama"


def test_chat_routes_to_localai_too():
    r = route(_CHAT, localai_enabled=True)
    assert r.decided, r.reason
    assert r.service == "localai"


def test_search_still_routes_to_searxng_under_localai():
    """LocalAI does not provide web search, so this capability must not be
    captured by the engine switch."""
    r = route(_SEARCH, localai_enabled=True)
    assert r.decided, r.reason
    assert r.service == "searxng"


def test_image_stays_on_comfyui_under_localai():
    """LocalAI can generate images, but ComfyUI is Tier 2 — a capability pipeline
    no engine ships. Over-routing here would quietly disable the Wan2.2-S2V and
    LivePortrait work."""
    r = route("draw a picture of a red fox in the snow", localai_enabled=True)
    assert r.decided, r.reason
    assert r.service == "comfyui"


def test_a_service_override_wins():
    r = route(_CODE, localai_enabled=True, service_overrides={"coding": "llama_cpp"})
    assert r.service == "llama_cpp"


def test_undecided_route_has_no_service():
    from puente.decide import LexicalBackend

    r = route("hmm", backend=LexicalBackend())
    assert not r.decided
    assert r.service is None
