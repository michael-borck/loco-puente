"""Portal page generator — creates a service launcher from puente.yml."""

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
}


def collect_services(config: PuenteConfig, host: str = "localhost") -> list[PortalService]:
    """Build a list of enabled services with their portal URLs."""
    services = []

    for svc_name, svc_class in ALL_SERVICES.items():
        if svc_name == "ollama":
            continue  # Ollama is a backend, not user-facing

        svc_config = getattr(config.services, svc_name, None)
        if svc_config is None or not svc_config.enabled:
            continue

        icon, display_name, desc = SERVICE_META.get(
            svc_name, ("🔧", svc_name, "")
        )
        port = svc_config.port or svc_class.default_port
        url = f"http://{host}:{port}"

        services.append(PortalService(
            name=display_name,
            icon=icon,
            description=desc,
            url=url,
        ))

    return services


def generate_portal(config: PuenteConfig, host: str = "localhost") -> str:
    """Render the portal HTML from the Jinja2 template."""
    services = collect_services(config, host)

    templates_dir = Path(__file__).parent / "templates" / "portal"
    env = Environment(loader=FileSystemLoader(str(templates_dir)))
    template = env.get_template("index.html.j2")

    return template.render(
        machine_name="LocoPuente",
        services=services,
    )


def write_portal(config: PuenteConfig, host: str = "localhost", output_dir: Path | None = None) -> Path:
    """Generate and write the portal index.html."""
    html = generate_portal(config, host)
    out_dir = output_dir or config.resolved_data_dir() / "portal"
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "index.html"
    path.write_text(html)
    return path
