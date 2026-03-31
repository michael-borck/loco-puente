"""Portal page generator — creates service launcher pages from puente.yml."""

from __future__ import annotations

from dataclasses import dataclass
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


# Icons and descriptions for the portal cards
SERVICE_META = {
    "open_webui": ("💬", "AI Chat", "Chat, voice, images, web search"),
    "vane": ("🔍", "AI Search", "Cited answers with sources"),
    "speaches": ("🎙️", "Voice", "Speech-to-text and text-to-speech"),
    "anythingllm": ("📚", "Knowledge Base", "Document Q&A workspaces"),
    "open_notebook": ("📓", "Research Notes", "Read, annotate, synthesise, podcast"),
    "comfyui": ("🎨", "Image Gen", "SD, SDXL, FLUX workflows"),
    "stirling_pdf": ("📄", "PDF Tools", "Merge, split, OCR, convert"),
    "excalidraw": ("✏️", "Whiteboard", "Collaborative diagrams"),
    "searxng": ("🌐", "Web Search", "Private search engine"),
    "citesight": ("📝", "Citation Checker", "Verify references and writing quality"),
    "jupyter": ("📒", "JupyterLab", "Browser-based Python notebooks"),
    "talkbuddy": ("🗣️", "TalkBuddy", "Conversation practice partner"),
    "studybuddy": ("🎓", "StudyBuddy", "AI-powered study companion"),
    "careercompass": ("🧭", "CareerCompass", "Career guidance and planning"),
}

# Student-facing portal: what users see
STUDENT_SERVICES = {
    "ai": {
        "label": "AI",
        "services": ["open_webui", "vane", "open_notebook"],
    },
    "tools": {
        "label": "Tools",
        "services": ["searxng", "stirling_pdf", "excalidraw", "citesight", "jupyter"],
    },
    "learning": {
        "label": "Learning",
        "services": ["talkbuddy", "studybuddy", "careercompass"],
    },
}

# Backend portal: admin/infrastructure services
BACKEND_SERVICES = {
    "inference": {
        "label": "Inference",
        "services": ["ollama"],
    },
    "backends": {
        "label": "Backend Services",
        "services": ["speaches", "comfyui", "anythingllm", "searxng"],
    },
}


# External apps — not in the stack, just portal links
EXTERNAL_APPS = {
    "talkbuddy": "https://talkbuddy.borck.education",
    "studybuddy": "https://studybuddy.borck.education",
    "careercompass": "https://careercompass.borck.education",
}


def _build_service(svc_name: str, config: PuenteConfig, host: str) -> PortalService | None:
    """Build a PortalService for a given service name."""
    # External apps (not in the stack)
    if svc_name in EXTERNAL_APPS:
        icon, display_name, desc = SERVICE_META.get(svc_name, ("🔧", svc_name, ""))
        return PortalService(
            name=display_name, icon=icon, description=desc, url=EXTERNAL_APPS[svc_name],
        )

    if svc_name == "ollama":
        # Special case: show Ollama instances
        if not config.services.ollama.enabled:
            return None
        ports = [str(i.port) for i in config.services.ollama.instances]
        return PortalService(
            name="Ollama",
            icon="🧠",
            description=f"LLM inference (ports {', '.join(ports)})",
            url=f"http://{host}:{config.services.ollama.instances[0].port}",
        )

    svc_config = getattr(config.services, svc_name, None)
    if svc_config is None or not svc_config.enabled:
        return None

    svc_class = ALL_SERVICES.get(svc_name)
    if not svc_class:
        return None

    icon, display_name, desc = SERVICE_META.get(svc_name, ("🔧", svc_name, ""))
    port = svc_config.port or svc_class.default_port
    url = f"http://{host}:{port}"

    return PortalService(name=display_name, icon=icon, description=desc, url=url)


def collect_sections(
    config: PuenteConfig, host: str, layout: dict[str, dict]
) -> list[PortalSection]:
    """Build sections of services for a portal view."""
    sections = []
    for section_info in layout.values():
        svcs = []
        for svc_name in section_info["services"]:
            svc = _build_service(svc_name, config, host)
            if svc:
                svcs.append(svc)
        if svcs:
            sections.append(PortalSection(label=section_info["label"], services=svcs))
    return sections


def generate_portal(
    config: PuenteConfig,
    host: str = "localhost",
    variant: str = "student",
) -> str:
    """Render a portal HTML page."""
    layout = STUDENT_SERVICES if variant == "student" else BACKEND_SERVICES
    sections = collect_sections(config, host, layout)

    if variant == "student":
        title = "LocoPuente"
        subtitle = "Local AI services. All data stays on this machine."
    else:
        title = "LocoPuente — Backend"
        subtitle = "Infrastructure and backend services."

    templates_dir = Path(__file__).parent / "templates" / "portal"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("index.html.j2")

    return template.render(
        machine_name=title,
        subtitle=subtitle,
        sections=sections,
    )


def write_portal(
    config: PuenteConfig,
    host: str = "localhost",
    output_dir: Path | None = None,
) -> Path:
    """Generate and write both portal pages."""
    out_dir = output_dir or config.resolved_data_dir() / "portal"
    out_dir.mkdir(parents=True, exist_ok=True)

    # Student portal (default)
    student_html = generate_portal(config, host, "student")
    (out_dir / "index.html").write_text(student_html)

    # Backend portal
    backend_html = generate_portal(config, host, "backend")
    backend_dir = out_dir / "backend"
    backend_dir.mkdir(parents=True, exist_ok=True)
    (backend_dir / "index.html").write_text(backend_html)

    return out_dir
