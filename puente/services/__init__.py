"""Service registry."""

from __future__ import annotations

from .anythingllm import AnythingLLMService
from .base import ServiceBase
from .citesight import CiteSightService
from .deeptutor import DeepTutorService
from .comfyui import ComfyUIService
from .excalidraw import ExcalidrawService
from .jupyter import JupyterService
from .ollama import OllamaService
from .open_notebook import OpenNotebookService
from .open_terminal import OpenTerminalService
from .open_webui import OpenWebUIService
from .searxng import SearXNGService
from .speaches import SpeachesService
from .stirling_pdf import StirlingPDFService
from .vane import VaneService

ALL_SERVICES: dict[str, type[ServiceBase]] = {
    "ollama": OllamaService,
    "open_webui": OpenWebUIService,
    "speaches": SpeachesService,
    "comfyui": ComfyUIService,
    "searxng": SearXNGService,
    "vane": VaneService,
    "anythingllm": AnythingLLMService,
    "open_notebook": OpenNotebookService,
    "open_terminal": OpenTerminalService,
    "stirling_pdf": StirlingPDFService,
    "excalidraw": ExcalidrawService,
    "citesight": CiteSightService,
    "jupyter": JupyterService,
    "deeptutor": DeepTutorService,
}
