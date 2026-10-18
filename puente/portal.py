"""Portal page generator — creates a service launcher from puente.yml."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from puente.models import PuenteConfig
from puente.services import ALL_SERVICES


@dataclass
class PortalService:
    name: str
    icon: str
    description: str
    url: str
    #: The API endpoint, when the service exposes one. Distinct from `url`,
    #: which is the human-facing interface. See docs/vision.md commitment 3 —
    #: a service can have both, either, or neither, and collapsing them into one
    #: link is how someone ends up pointing their script at a web GUI.
    api_url: str | None = None
    #: The API's shape, for someone deciding whether they can use it.
    api_kind: str = ""
    #: True when `url` is itself an API rather than an interface — Ollama has an
    #: API and no real web UI of its own, so its card must say so rather than
    #: presenting a JSON endpoint as something to click.
    url_is_api: bool = False


#: Services whose primary surface is an API with no useful web interface.
#: Ollama serves a JSON root; linking it as though it were an app is misleading.
#: LocalAI is the exception among the engines — it does have a usable WebUI, so
#: it gets both an interface link and an API link.
API_ONLY = {"ollama", "llama_cpp", "speaches", "uptime_kuma", "tutor_admin"}

#: What kind of API each service speaks, for someone deciding if they can use it.
API_KIND = {
    "ollama": "OpenAI-compatible",
    "localai": "OpenAI + Anthropic + ElevenLabs",
    "llama_cpp": "OpenAI-compatible",
    "speaches": "OpenAI-compatible",
    "open_webui": "OpenAI-compatible",
    "searxng": "JSON",
    "comfyui": "JSON (prompt/history)",
    "swarmui": "JSON",
    "voicebox": "REST",
    "ace_step": "REST",
    "anythingllm": "REST",
    "vane": "JSON",
    "citesight": "JSON",
    "deeptutor": "REST",
    "uptime_kuma": "REST",
    "stirling_pdf": "REST",
    "presenton": "REST + MCP",
    "citesight_alt": "JSON",
}


@dataclass
class PortalSection:
    label: str
    services: list[PortalService]
    #: True for a section that should render dominant — the "Start Here"
    #: harness cards of the default view (Decision J: the portal leads with
    #: the 80% surface, and the grid gives it room).
    primary: bool = False


@dataclass
class PortalView:
    id: str
    label: str
    sections: list[PortalSection] = field(default_factory=list)


# Icons and descriptions for the portal cards
SERVICE_META = {
    "open_webui": ("💬", "AI Chat", "Chat, voice, images, web search"),
    "vane": ("🔍", "AI Search", "Cited answers with sources"),
    "speaches": ("🎙️", "Voice", "Speech-to-text and text-to-speech"),
    "anythingllm": ("📚", "Knowledge Base", "Document Q&A workspaces"),
    "open_notebook": ("📓", "Research Notes", "Read, annotate, synthesise, podcast"),
    "comfyui": ("🎨", "Image Workflows", "Node-based SD, SDXL, FLUX (power users)"),
    "swarmui": ("🖼️", "Image Gen", "Type a prompt, get a picture"),
    "musicgen": ("🎵", "Audio Gen", "MusicGen, AudioGen, Bark, Tortoise, more"),
    "fooocus": ("🪄", "Fooocus", "Alternative image UI — auto-tuned SDXL"),
    "stirling_pdf": ("📄", "PDF Tools", "Merge, split, OCR, convert"),
    "presenton": ("📽️", "Presenton", "AI slide decks — prompt or document to editable PPTX"),
    "excalidraw": ("✏️", "Whiteboard", "Collaborative diagrams"),
    "searxng": ("🌐", "Web Search", "Private search engine"),
    "citesight": ("📝", "Citation Checker", "Verify references and writing quality"),
    "jupyter": ("📒", "JupyterLab", "Browser-based Python notebooks"),
    "open_terminal": ("⚡", "Code Sandbox", "Python execution, PDF/DOCX generation"),
    "deeptutor": ("🎓", "DeepTutor", "Personalised learning — quizzes, deep solve, research"),
    "voicebox": ("🗣️", "Voicebox", "Voice cloning + TTS studio"),
    "librechat": ("💬", "LibreChat", "Multi-provider chat UI (evaluating)"),
    "chatterbox": ("🔊", "Chatterbox", "Voice-cloning TTS server (evaluating)"),
    "glances": ("📊", "System Monitor", "CPU, RAM, disk, GPU, containers"),
    "uptime_kuma": ("🟢", "Uptime Kuma", "Service uptime monitoring + alerts"),
}

# Hostnames this deployment published historically. NOT a fallback — nothing
# reads this to build a link. It exists for one reason: `puente doctor` uses it
# to spot a stale `proxy:` block still pointing at a host this machine no longer
# serves, which would send a student clicking the launcher page to another box.
#
# A service's `proxy:` block in puente.yml is the single source of truth. A
# service with no block links to host:port on the machine the portal was
# generated for.
FOREIGN_PROXY_HOSTS = {
    "chat.locopuente.org",
    "search.locopuente.org",
    "notes.locopuente.org",
    "pdf.locopuente.org",
    "whiteboard.locopuente.org",
    "cite.locopuente.org",
    "swarmui.locopuente.org",
    "musicgen.locopuente.org",
    "fooocus.locopuente.org",
    "voice.locopuente.org",
}

# View definitions.
#
# Two views, split by BEHAVIOUR not by role (Decision J): the chat view is the
# 80% — whichever harness won Decision H, leading — and the power view is the
# full app grid for people who want the individual surfaces. The portal is a
# router, never an app: it links to surfaces, it does not embed them.
#
# A view only renders if at least one of its services is enabled, so a fresh
# install with the harness off shows just the power grid — and the harness
# candidates below silently vanish until one is enabled.
VIEWS = {
    "chat": {
        "label": "Chat",
        "sections": [
            # The harness candidates, in preference order. Decision H keeps
            # Open WebUI as incumbent until the Odysseus experiment decides;
            # LibreChat and AnythingLLM remain listed while Decisions H/B are
            # open rather than pretending a choice was made.
            {
                "label": "Start Here",
                "services": ["open_webui", "librechat", "anythingllm"],
                "primary": True,
            },
        ],
    },
    "power": {
        "label": "Power User",
        "sections": [
            {"label": "Search & Research", "services": ["vane", "searxng", "open_notebook", "deeptutor", "citesight"]},
            {"label": "Create", "services": ["comfyui", "swarmui", "fooocus", "presenton", "ace_step", "musicgen"]},
            {"label": "Voice", "services": ["voicebox", "speaches", "chatterbox"]},
            {"label": "Inference", "services": ["ollama", "localai", "llama_cpp"]},
            {"label": "Code & Notes", "services": ["jupyter", "open_terminal", "nodepad"]},
            {"label": "Documents", "services": ["stirling_pdf", "excalidraw"]},
            {"label": "Infrastructure", "services": ["glances", "uptime_kuma", "tutor_admin", "caddy"]},
            # Auto-collects any enabled service whose config has `review: true`.
            # Filled at build time so adding/removing review services requires
            # no changes here.
            {"label": "Under Evaluation", "services": "__review__"},
        ],
    },
}


def _api_kind_for(svc_name: str, data_dir: str | None) -> str:
    """API kind for a service, from API_KIND or falling back to the catalog.

    Catalog entries carry their own `api.kind`, so a service added to the catalog
    needs no edit here — otherwise every Tier 3 entry would have to be listed in
    two places, and one of them would inevitably be forgotten.
    """
    kind = API_KIND.get(svc_name)
    if kind:
        return kind
    from .catalog import load_entries

    entry = load_entries(data_dir).get(svc_name)
    return entry.api.kind if entry and entry.api else ""


def _build_service(svc_name: str, config: PuenteConfig, host: str) -> PortalService | None:
    """Build a PortalService for a given service name."""
    # Ollama (special case)
    if svc_name == "ollama":
        if not config.services.ollama.enabled:
            return None
        ports = [str(i.port) for i in config.services.ollama.instances]
        api = f"http://{host}:{config.services.ollama.instances[0].port}"
        return PortalService(
            name="Ollama",
            icon="🧠",
            description=f"LLM inference (ports {', '.join(ports)})",
            url=api,
            api_url=api,
            api_kind=API_KIND["ollama"],
            url_is_api=True,
        )

    # LocalAI has both a real WebUI and an API, so it is not an API-only card —
    # but the API is the reason most people will point a client at it, so it
    # gets its own link rather than being folded into the interface URL.
    if svc_name == "localai":
        if not config.services.localai.enabled:
            return None
        port = config.services.localai.port or 8080
        proxy = config.services.localai.proxy
        if isinstance(proxy, list):
            proxy = proxy[0] if proxy else None
        url = f"https://{proxy.host}" if proxy else f"http://{host}:{port}"
        return PortalService(
            name="LocalAI",
            icon="🧠",
            description="Local AI engine — text, image, voice, embeddings",
            url=url,
            api_url=url,
            api_kind=_api_kind_for(svc_name, None),
            url_is_api=False,
        )

    # Stack services
    svc_config = getattr(config.services, svc_name, None)
    if svc_config is None or not svc_config.enabled:
        return None

    svc_class = ALL_SERVICES.get(svc_name)
    if not svc_class:
        return None

    icon, display_name, desc = SERVICE_META.get(svc_name, ("🔧", svc_name, ""))

    # A service may front several hostnames (swarmui, voicebox, portal each do),
    # in which case `proxy` is a list — the first entry is the canonical one.
    proxy = getattr(svc_config, "proxy", None)
    if isinstance(proxy, list):
        proxy = proxy[0] if proxy else None

    port = svc_config.port or svc_class.default_port
    if proxy is not None:
        url = f"https://{proxy.host}"
    else:
        # No declared proxy block → link to this machine on its own port. Never
        # fall back to a hardcoded hostname: see FOREIGN_PROXY_HOSTS above.
        url = f"http://{host}:{port}"

    # Same host as the interface, but named as an API so it can be labelled
    # separately. For a proxied service the API is reached through the same
    # hostname — Caddy fronts both.
    api_kind = _api_kind_for(svc_name, None)
    api_url = url if api_kind else None

    return PortalService(
        name=display_name,
        icon=icon,
        description=desc,
        url=url,
        api_url=api_url,
        api_kind=api_kind,
        url_is_api=svc_name in API_ONLY,
    )


def _review_service_names(config: PuenteConfig) -> list[str]:
    """Names of every enabled service whose config has `review: true`."""
    out = []
    for svc_name in ALL_SERVICES:
        if svc_name == "ollama":
            continue
        svc_config = getattr(config.services, svc_name, None)
        if svc_config is None or not svc_config.enabled:
            continue
        if getattr(svc_config, "review", False):
            out.append(svc_name)
    return out


def build_views(config: PuenteConfig, host: str) -> list[PortalView]:
    """Build all portal views with their sections and services."""
    views = []
    for view_id, view_def in VIEWS.items():
        sections = []
        for section_def in view_def["sections"]:
            service_names = section_def["services"]
            if service_names == "__review__":
                service_names = _review_service_names(config)
            svcs = []
            for svc_name in service_names:
                svc = _build_service(svc_name, config, host)
                if svc:
                    svcs.append(svc)
            if svcs:
                sections.append(
                    PortalSection(
                        label=section_def["label"],
                        services=svcs,
                        primary=section_def.get("primary", False),
                    )
                )
        if sections:
            views.append(PortalView(id=view_id, label=view_def["label"], sections=sections))

    # Operator-declared cards (PortalConfig.extra_cards) for services Puente
    # does not manage — experiments, hand-run containers, other boxes. A card
    # FORCES its view to render: the operator added it deliberately, so an
    # otherwise-empty view must still appear rather than swallow the card.
    extras = getattr(config.services.portal, "extra_cards", None) or []
    by_view: dict[str, list[PortalService]] = {}
    for card in extras:
        by_view.setdefault(card.view, []).append(
            PortalService(
                name=card.name,
                icon=card.icon,
                description=card.description,
                url=card.url,
                api_url=card.api_url,
                api_kind=card.api_kind,
            )
        )
    for view_id, cards in by_view.items():
        view = next((v for v in views if v.id == view_id), None)
        if view is None:
            view = PortalView(id=view_id, label=VIEWS[view_id]["label"], sections=[])
            views.append(view)
            views.sort(key=lambda v: list(VIEWS).index(v.id))
        view.sections.append(
            PortalSection(label="External", services=cards, primary=False)
        )

    return views


def generate_portal(config: PuenteConfig, host: str = "localhost") -> str:
    """Render the portal HTML."""
    views = build_views(config, host)

    # The view shown on load. Configurable (PortalConfig.default_view) because
    # Decision J's whole point is that the default surface is the harness; if
    # the configured view has no enabled services, fall back to the first that
    # renders rather than a landing page with no visible content.
    configured = config.services.portal.default_view
    default_id = configured if any(v.id == configured for v in views) else (
        views[0].id if views else ""
    )

    templates_dir = Path(__file__).parent / "templates" / "portal"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("index.html.j2")

    return template.render(
        title="Closing the Gap",
        subtitle="Local AI. All data stays on this machine.",
        views=views,
        default_id=default_id,
    )


def write_portal(
    config: PuenteConfig,
    host: str = "localhost",
    output_dir: Path | None = None,
) -> Path:
    """Generate and write the portal page."""
    out_dir = output_dir or config.resolved_data_dir() / "portal"
    out_dir.mkdir(parents=True, exist_ok=True)

    html = generate_portal(config, host)
    path = out_dir / "index.html"
    path.write_text(html)

    # Clean up old backend subdirectory if it exists
    backend_dir = out_dir / "backend"
    if backend_dir.exists():
        import shutil
        shutil.rmtree(backend_dir)

    return out_dir
