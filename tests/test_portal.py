"""Tests for the portal's two-surface model.

A service has an *interface* (something a person opens) and an *API* (something
your code calls). They are not the same thing, and conflating them is how
someone ends up pointing their script at a web GUI — or clicking a card that
turns out to be a JSON endpoint.

These pin the distinction, including the awkward cases: Ollama has an API and
almost no interface, and Excalidraw has an interface and nothing to automate.
"""

from __future__ import annotations


import pytest

from puente.models import PuenteConfig
from puente.portal import API_KIND, API_ONLY, build_views, generate_portal


def _config(**services) -> PuenteConfig:
    base = {"ollama": {"enabled": False}, "open_webui": {"enabled": False},
            "searxng": {"enabled": False}}
    base.update(services)
    return PuenteConfig.model_validate({"services": base})


def _card(cfg: PuenteConfig, host: str = "10.0.0.5", view: str | None = None):
    """Every card across every view, unless one view is named.

    Which view a service lands in is a presentation choice and changes as the
    views are reorganised; a test about the API surface should not break when
    Excalidraw moves between the student and admin views.
    """
    for v in build_views(cfg, host):
        if view is not None and v.id != view:
            continue
        for s in v.sections:
            for svc in s.services:
                yield svc


def _find(cfg, name=None, **kw):
    """The single card for `name`, or the only card when there is just one."""
    cards = list(_card(cfg, **kw))
    if name is None:
        return cards[0]
    return next((s for s in cards if s.name == name), None)


# --------------------------------------------------------------------------
# the distinction
# --------------------------------------------------------------------------


def test_a_service_may_have_both_surfaces():
    c = _find(_config(comfyui={"enabled": True,
                               "proxy": {"host": "img.example.org", "auth": "none"}}))
    assert c.url and c.api_url
    assert c.api_kind


def test_a_service_may_have_only_an_interface():
    """Excalidraw is a drawing surface with nothing to automate. Inventing an API
    endpoint for it would be a lie in the UI."""
    c = _find(_config(excalidraw={"enabled": True,
                                 "proxy": {"host": "board.example.org", "auth": "none"}}))
    assert c.url
    assert c.api_url is None


def test_a_service_may_be_api_only():
    """Ollama serves a JSON root. Presenting that as a thing to click is
    misleading, so it is marked rather than dressed up as an app."""
    c = _find(_config(ollama={"enabled": True}))
    assert c.url_is_api is True
    assert c.api_url == c.url


def test_ollama_advertises_an_openai_compatible_api():
    c = _find(_config(ollama={"enabled": True}))
    assert "OpenAI" in c.api_kind


# --------------------------------------------------------------------------
# declared kinds exist
# --------------------------------------------------------------------------


def test_api_kinds_only_name_real_services():
    from puente.services import ALL_SERVICES

    unknown = {k for k in API_KIND if k not in ALL_SERVICES and not k.endswith("_alt")}
    assert not unknown, f"API_KIND names services that do not exist: {unknown}"


def test_api_only_set_only_names_real_services():
    from puente.services import ALL_SERVICES

    assert not (set(API_ONLY) - set(ALL_SERVICES))


def test_every_llm_backend_is_openai_compatible():
    """The whole reason either backend is usable: existing clients speak it."""
    assert "OpenAI" in API_KIND["ollama"]
    assert "OpenAI" in API_KIND["llama_cpp"]
    assert "OpenAI" in API_KIND["speaches"]


# --------------------------------------------------------------------------
# rendering
# --------------------------------------------------------------------------


def test_api_line_is_rendered_with_kind_and_url():
    html = generate_portal(
        _config(comfyui={"enabled": True,
                         "proxy": {"host": "img.example.org", "auth": "none"}}), "10.0.0.5"
    )
    assert 'class="card-api-line"' in html
    assert "JSON (prompt/history)" in html
    assert "img.example.org" in html


def test_interface_only_service_renders_no_api_line():
    html = generate_portal(
        _config(excalidraw={"enabled": True,
                            "proxy": {"host": "board.example.org", "auth": "none"}}),
        "10.0.0.5",
    )
    assert 'class="card-api-line"' not in html


def test_api_only_service_is_visually_marked():
    """Dashed border, so the card does not look like a clickable app."""
    html = generate_portal(_config(ollama={"enabled": True}), "10.0.0.5")
    assert "card-api\"" in html or "card-api " in html


def test_interface_link_still_works():
    """The API line is a reference, not a replacement — the card must remain
    clickable."""
    html = generate_portal(
        _config(comfyui={"enabled": True,
                         "proxy": {"host": "img.example.org", "auth": "none"}}), "10.0.0.5"
    )
    assert 'class="card-link"' in html
    assert 'href="https://img.example.org"' in html


def test_proxied_api_reuses_the_interface_hostname():
    """Caddy fronts both, so the API is reached through the same host."""
    c = _find(_config(searxng={"enabled": True,
                               "proxy": {"host": "s.example.org", "auth": "none"}}))
    assert c.api_url == c.url == "https://s.example.org"


# --------------------------------------------------------------------------
# regression: the surface split must not break the card list
# --------------------------------------------------------------------------


def test_each_service_renders_its_own_card():
    """Guards a bug introduced while adding the two surfaces: every service was
    rendering as 'Ollama' because the special case stopped returning."""
    cfg = _config(
        ollama={"enabled": True},
        open_webui={"enabled": True},
        searxng={"enabled": True},
    )
    names = {s.name for s in _card(cfg)}
    assert "Ollama" in names
    assert len(names) == len(list(_card(cfg))), "duplicate cards for one service"


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])