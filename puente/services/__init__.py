"""Service registry."""

from __future__ import annotations

from .anythingllm import AnythingLLMService
from .caddy import CaddyService
from .chatterbox import ChatterboxService
from .glances import GlancesService
from .base import ServiceBase
from .citesight import CiteSightService
from .deeptutor import DeepTutorService
from .comfyui import ComfyUIService
from .excalidraw import ExcalidrawService
from .fooocus import FooocusService
from .jupyter import JupyterService
from .librechat import LibreChatService
from .musicgen import MusicGenService
from .nodepad import NodepadService
from .ollama import OllamaService
from .open_notebook import OpenNotebookService
from .open_terminal import OpenTerminalService
from .open_webui import OpenWebUIService
from .portal import PortalService
from .searxng import SearXNGService
from .speaches import SpeachesService
from .stirling_pdf import StirlingPDFService
from .swarmui import SwarmUIService
from .vane import VaneService
from .voicebox import VoiceboxService

ALL_SERVICES: dict[str, type[ServiceBase]] = {
    "ollama": OllamaService,
    "open_webui": OpenWebUIService,
    "speaches": SpeachesService,
    "comfyui": ComfyUIService,
    "searxng": SearXNGService,
    "vane": VaneService,
    "anythingllm": AnythingLLMService,
    "chatterbox": ChatterboxService,
    "glances": GlancesService,
    "open_notebook": OpenNotebookService,
    "open_terminal": OpenTerminalService,
    "stirling_pdf": StirlingPDFService,
    "excalidraw": ExcalidrawService,
    "citesight": CiteSightService,
    "jupyter": JupyterService,
    "librechat": LibreChatService,
    "deeptutor": DeepTutorService,
    "musicgen": MusicGenService,
    "nodepad": NodepadService,
    "swarmui": SwarmUIService,
    "fooocus": FooocusService,
    "voicebox": VoiceboxService,
    "portal": PortalService,
    "caddy": CaddyService,
}
