"""Service registry."""

from __future__ import annotations

from .anythingllm import AnythingLLMService
from .base import ServiceBase
from .comfyui import ComfyUIService
from .excalidraw import ExcalidrawService
from .ollama import OllamaService
from .open_notebook import OpenNotebookService
from .open_webui import OpenWebUIService
from .perplexica import PerplexicaService
from .searxng import SearXNGService
from .speaches import SpeachesService
from .stirling_pdf import StirlingPDFService

ALL_SERVICES: dict[str, type[ServiceBase]] = {
    "ollama": OllamaService,
    "open_webui": OpenWebUIService,
    "speaches": SpeachesService,
    "comfyui": ComfyUIService,
    "searxng": SearXNGService,
    "perplexica": PerplexicaService,
    "anythingllm": AnythingLLMService,
    "open_notebook": OpenNotebookService,
    "stirling_pdf": StirlingPDFService,
    "excalidraw": ExcalidrawService,
}
