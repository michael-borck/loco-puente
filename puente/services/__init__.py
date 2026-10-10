"""Service registry.

Three tiers, split by ownership rather than by whether a service is "AI"
(ADR0012):

  * **Ours** — LocalAI, hardware detection, decision routing, Caddy, the tutor
    admin. Anything with real logic on this side of the line.
  * **Capability pipelines LocalAI cannot reach** — ComfyUI and its node
    ecosystems (Wan2.2-S2V, LivePortrait, SadTalker, Wav2Lip), SwarmUI.
    Hand-written, because no engine is going to ship these.
  * **Catalog** — Jupyter, Excalidraw, Stirling PDF and friends. Declarations in
    `puente/catalog/*.yml`, materialised into ServiceBase subclasses here so
    that compose generation, the portal, `puente doctor` and `puente status` need
    no special case for any of them.

Catalog entries marked `implementation: builtin` keep a hand-written class and
appear in this registry explicitly — they are declared for their metadata, not
generated.
"""

from __future__ import annotations

from .ace_step import AceStepService
from .anythingllm import AnythingLLMService
from .base import ServiceBase
from .caddy import CaddyService
from .chatterbox import ChatterboxService
from .glances import GlancesService
from .citesight import CiteSightService
from .deeptutor import DeepTutorService
from .comfyui import ComfyUIService
from .fooocus import FooocusService
from .llama_cpp import LlamaCppService
from .librechat import LibreChatService
from .localai import LocalAIService
from .musicgen import MusicGenService
from .ollama import OllamaService
from .open_terminal import OpenTerminalService
from .open_webui import OpenWebUIService
from .portal import PortalService
from .searxng import SearXNGService
from .speaches import SpeachesService
from .swarmui import SwarmUIService
from .tutor_admin import TutorAdminService
from .uptime_kuma import UptimeKumaService
from .vane import VaneService
from .voicebox import VoiceboxService

#: Hand-written implementations, in the order the portal and CLI show them.
_HANDWRITTEN: dict[str, type[ServiceBase]] = {
    "ollama": OllamaService,
    "localai": LocalAIService,
    "open_webui": OpenWebUIService,
    "speaches": SpeachesService,
    "comfyui": ComfyUIService,
    "vane": VaneService,
    "chatterbox": ChatterboxService,
    "glances": GlancesService,
    "citesight": CiteSightService,
    "open_terminal": OpenTerminalService,
    "deeptutor": DeepTutorService,
    "musicgen": MusicGenService,
    "librechat": LibreChatService,
    "swarmui": SwarmUIService,
    "fooocus": FooocusService,
    "tutor_admin": TutorAdminService,
    "llama_cpp": LlamaCppService,
    "ace_step": AceStepService,
    "voicebox": VoiceboxService,
    "uptime_kuma": UptimeKumaService,
    "portal": PortalService,
    "caddy": CaddyService,
}

#: Catalog entries with real lifecycle logic, which the catalog cannot express.
#: Their capability and hardware metadata still comes from the catalog; only the
#: behaviour is hand-written. See the module docstring.
#:
#: - SearXNG's settings.yml must be seeded before the container's first read,
#:   because SearXNG reads it once at boot and ignores later changes.
#: - AnythingLLM's `storage_path` adopts an existing install in place, so
#:   migrating it must not lose workspaces, embeddings or the vector DB.
_BUILTIN_CATALOG: dict[str, type[ServiceBase]] = {
    "searxng": SearXNGService,
    "anythingllm": AnythingLLMService,
}


def _generate_catalog_services() -> dict[str, type[ServiceBase]]:
    """Materialise a ServiceBase subclass for every generated catalog entry.

    A malformed bundled catalog entry raises here at import, not later — a
    catalog that fails to load should break every command loudly rather than
    silently produce a stack with a missing service.

    Builtin entries are skipped: their hand-written class wins, because the
    class is the reason they are builtin.
    """
    from ..catalog import _service_class, load_entries

    out: dict[str, type[ServiceBase]] = {}
    for entry in load_entries().values():
        if entry.implementation != "generated":
            continue
        out[entry.id] = _service_class(entry)
    return out


#: Every service the stack knows about: hand-written, then builtin catalog
#: entries, then generated ones.
ALL_SERVICES: dict[str, type[ServiceBase]] = {
    **_HANDWRITTEN,
    **_BUILTIN_CATALOG,
    **_generate_catalog_services(),
}
