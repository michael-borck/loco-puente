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


@dataclass
class PortalSection:
    label: str
    services: list[PortalService]


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
    "excalidraw": ("✏️", "Whiteboard", "Collaborative diagrams"),
    "searxng": ("🌐", "Web Search", "Private search engine"),
    "citesight": ("📝", "Citation Checker", "Verify references and writing quality"),
    "jupyter": ("📒", "JupyterLab", "Browser-based Python notebooks"),
    "open_terminal": ("⚡", "Code Sandbox", "Python execution, PDF/DOCX generation"),
    "deeptutor": ("🎓", "DeepTutor", "Personalised learning — quizzes, deep solve, research"),
}

# Proxy URLs — services accessible via reverse proxy (overrides host:port)
PROXY_URLS = {
    "open_webui": "https://chat.locopuente.org",
    "vane": "https://search.locopuente.org",
    "open_notebook": "https://notes.locopuente.org",
    "stirling_pdf": "https://pdf.locopuente.org",
    "excalidraw": "https://whiteboard.locopuente.org",
    "citesight": "https://cite.locopuente.org",
    "swarmui": "https://swarmui.locopuente.org",
    "musicgen": "https://musicgen.locopuente.org",
    "fooocus": "https://fooocus.locopuente.org",
}

# View definitions
VIEWS = {
    "student": {
        "label": "Student",
        "sections": [
            {"label": "AI", "services": ["open_webui", "vane", "open_notebook", "deeptutor"]},
            {"label": "Creative", "services": ["swarmui", "musicgen"]},
            {"label": "Tools", "services": ["stirling_pdf", "excalidraw", "citesight"]},
        ],
    },
    "admin": {
        "label": "Admin",
        "sections": [
            {"label": "Inference", "services": ["ollama"]},
            {
                "label": "Backend Services",
                "services": ["speaches", "comfyui", "anythingllm", "open_terminal"],
            },
            {"label": "Power Tools", "services": ["searxng", "jupyter"]},
            # The "Under Evaluation" section auto-collects any enabled service
            # whose config has `review: true`. The list is filled at build time
            # by `build_views` so adding/removing review services requires no
            # changes here.
            {"label": "Under Evaluation", "services": "__review__"},
        ],
    },
}


def _build_service(svc_name: str, config: PuenteConfig, host: str) -> PortalService | None:
    """Build a PortalService for a given service name."""
    # Ollama (special case)
    if svc_name == "ollama":
        if not config.services.ollama.enabled:
            return None
        ports = [str(i.port) for i in config.services.ollama.instances]
        return PortalService(
            name="Ollama",
            icon="🧠",
            description=f"LLM inference (ports {', '.join(ports)})",
            url=f"http://{host}:{config.services.ollama.instances[0].port}",
        )

    # Stack services
    svc_config = getattr(config.services, svc_name, None)
    if svc_config is None or not svc_config.enabled:
        return None

    svc_class = ALL_SERVICES.get(svc_name)
    if not svc_class:
        return None

    icon, display_name, desc = SERVICE_META.get(svc_name, ("🔧", svc_name, ""))

    # Use proxy URL if available, otherwise fall back to host:port
    if svc_name in PROXY_URLS:
        url = PROXY_URLS[svc_name]
    else:
        port = svc_config.port or svc_class.default_port
        url = f"http://{host}:{port}"

    return PortalService(name=display_name, icon=icon, description=desc, url=url)


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
                sections.append(PortalSection(label=section_def["label"], services=svcs))
        if sections:
            views.append(PortalView(id=view_id, label=view_def["label"], sections=sections))
    return views


def generate_portal(config: PuenteConfig, host: str = "localhost") -> str:
    """Render the portal HTML."""
    views = build_views(config, host)

    templates_dir = Path(__file__).parent / "templates" / "portal"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("index.html.j2")

    return template.render(
        title="Closing the Gap",
        subtitle="Local AI. All data stays on this machine.",
        views=views,
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
