"""Service catalog — declarations for third-party images.

Puente used to hand-write a service class per capability. That was the wrong unit
of work: for a Jupyter image or a PDF toolkit, the class contributed a compose
fragment, a description and a port. Docker Compose already knows how to run a
container; what it does not know is *which* image to pin, what hardware it needs,
or what capability it provides.

So a Tier 3 service is now a **declaration** (ADR0012):

    id: stirling_pdf
    image: docker.io/stirlingtools/stirling-pdf:2
    provides: [documents]
    needs_vram_mb: 0

and `puente/services/__init__.py` materialises a :class:`~puente.services.base.
ServiceBase` subclass from it at import time. Everything downstream — compose
generation, the portal, `puente doctor`, `puente status`, `puente enable` — reads
`ALL_SERVICES` and needs no special case for any of this.

Two things are deliberately *not* generated:

  * Anything with real lifecycle logic. AnythingLLM's `storage_path` adopts an
    existing install in place; SearXNG's settings file must be seeded before the
    container's first read. Those declare ``implementation: builtin`` and keep a
    hand-written class, while taking their capability and hardware metadata from
    here so there is still one source of truth.

  * Anything LocalAI can serve. The engine slot is LocalAI's (ADR0012); a catalog
    entry for an image-generation engine is the duplication this ADR exists to
    stop.

The catalog is **opt-in**. Nothing here is enabled by default — see ADR0012.
Enabling a profile or a single entry is an explicit act.

Catalog files are read from two places, later wins:

  * ``puente/catalog/*.yml`` — bundled with the package, the curated set.
  * ``{data_dir}/catalog/*.yml`` — the operator's own entries, so someone can add
    a service Puente has never heard of without a fork.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator

#: Bundled catalog. Shipped as package data (see pyproject's package-data).
BUNDLED_CATALOG_DIR = Path(__file__).parent / "catalog"

#: Operator-supplied catalog, relative to the stack's data_dir.
USER_CATALOG_DIRNAME = "catalog"


class CatalogApi(BaseModel):
    """The API surface, when one exists.

    Separate from `interface` because a service can have both, either or neither,
    and collapsing them is how someone ends up pointing a script at a web GUI
    (docs/vision.md, commitment 3).
    """

    #: Path within the service, e.g. "/v1".
    path: str = "/"
    #: What protocol to expect — "OpenAI-compatible", "REST", "JSON".
    kind: str = "REST"


class CatalogEntry(BaseModel):
    """One declared third-party service."""

    #: Config key. Underscores; matches the existing service naming.
    id: str
    #: Human name for the portal and CLI.
    name: str
    description: str

    #: Pinned image reference. A floating tag is a bug waiting to happen — the
    #: pin is what makes `puente doctor` able to say what someone is running.
    image: str

    #: Port the container listens on.
    container_port: int
    #: Host port when the entry is enabled.
    default_port: int | None = None

    #: Capabilities this entry provides, matched against `puente capabilities`
    #: names. Declared so hardware fit can be reasoned about without running it.
    provides: list[str] = Field(default_factory=list)

    #: VRAM this entry needs when it runs a model. Zero for anything CPU-only,
    #: which is the honest answer for Jupyter, Excalidraw and Stirling PDF.
    needs_vram_mb: int = 0

    #: True only when the image genuinely requires CUDA.
    needs_gpu: bool = False

    #: Human-facing web interface, if any.
    interface: CatalogApi | None = None
    #: Programmatic API, if any.
    api: CatalogApi | None = None

    #: Profiles that enable this entry, e.g. ["office"]. See PROFILES.
    profiles: list[str] = Field(default_factory=list)

    #: Built from a local context instead of pulled — for images Puente publishes
    #: itself under its own GHCR namespace.
    build_context: str | None = None
    puente_published: bool = False

    #: Container path -> host path template. `{data_dir}` expands to the stack's
    #: data dir; `{port}` to the resolved host port.
    volumes: dict[str, str] = Field(default_factory=dict)
    #: Environment defaults. Same template substitution as volumes. Values here
    #: are defaults; `services.<id>.environment` in puente.yml overrides them.
    environment: dict[str, str] = Field(default_factory=dict)
    #: Extra host:container port mappings, beyond the primary one. Templates
    #: resolve here too, so a second port can reference the first.
    extra_ports: list[str] = Field(default_factory=list)
    extra_hosts: list[str] = Field(default_factory=list)

    restart: str = "unless-stopped"
    managed: bool = True

    #: "builtin" when a hand-written class implements this entry's behaviour and
    #: only the metadata lives here. See the module docstring.
    implementation: Literal["generated", "builtin"] = "generated"

    #: Where the upstream project lives. Shown by `puente catalog`.
    repo: str | None = None

    @field_validator("id")
    @classmethod
    def _valid_id(cls, v: str) -> str:
        if not v or not v.replace("_", "").isalnum():
            raise ValueError(
                f"catalog id {v!r} must be alphanumeric with underscores"
            )
        return v

    @field_validator("image")
    @classmethod
    def _pinned_image(cls, v: str) -> str:
        """Reject a floating tag or a bare name.

        Not pedantry: the pin is the only record of what someone is running, and
        `latest` means a `puente up` six months from now silently runs different
        code than the one that was tested.
        """
        if ":" not in v.rsplit("/", 1)[-1]:
            raise ValueError(
                f"image {v!r} has no tag — pin one (e.g. ':2', ':v1.2.3') so the "
                f"stack is reproducible"
            )
        return v

    def host_port(self, override: int | None = None) -> int:
        return override or self.default_port or self.container_port


#: Named bundles. A profile is just a list of catalog ids; there is no profile
#: logic beyond that, deliberately — `puente enable --profile office` should do
#: nothing a `for` loop would not.
PROFILES: dict[str, list[str]] = {
    # The office tools. Deliberately not default: someone who only wants a chat
    # interface should not end up with a whiteboard and a notebook server.
    "office": ["stirling_pdf", "excalidraw", "jupyter"],
    # What a research workflow needs: private search and document-grounded notes.
    "research": ["searxng", "anythingllm", "open_notebook"],
    # Everything the stack knows how to declare. For `puente catalog --all`.
    "all": [],
}


# --------------------------------------------------------------------------
# loading
# --------------------------------------------------------------------------


def entry_for(service_id: str, data_dir: Path | None = None) -> CatalogEntry | None:
    """One catalog entry by id, or None when it is hand-written instead."""
    return load_entries(data_dir).get(service_id)


def needs_vram_gb(service_id: str, data_dir: Path | None = None) -> float:
    """VRAM an entry needs, in GB. Zero for anything with no catalog entry.

    Lets capability assessment read hardware fit from one place instead of a
    second table in `capabilities.py` that would drift.
    """
    entry = entry_for(service_id, data_dir)
    return entry.needs_vram_mb / 1024.0 if entry else 0.0


def _read_dir(directory: Path) -> list[CatalogEntry]:
    """Parse every *.yml in `directory`. A bad file raises — never skips.

    Silently ignoring a malformed catalog entry would produce a stack that is
    missing a service the operator asked for, with no message explaining why.
    """
    if not directory.is_dir():
        return []
    entries: list[CatalogEntry] = []
    for path in sorted(directory.glob("*.yml")) + sorted(directory.glob("*.yaml")):
        raw = yaml.safe_load(path.read_text()) or {}
        items = raw.get("services", raw) if isinstance(raw, dict) else raw
        if not items:
            continue
        # Allow either a single entry or a list per file.
        if isinstance(items, dict):
            items = [items]
        for item in items:
            entries.append(CatalogEntry.model_validate(item))
    return entries


def load_entries(data_dir: Path | None = None) -> dict[str, CatalogEntry]:
    """Bundled catalog overlaid with the operator's, keyed by id.

    A user entry with the same id *replaces* the bundled one rather than raising:
    pinning a different version of a catalogued image is the single most likely
    thing someone will want to do, and it should not require deleting a file out
    of an installed package.
    """
    entries: dict[str, CatalogEntry] = {}
    for entry in _read_dir(BUNDLED_CATALOG_DIR):
        entries[entry.id] = entry
    if data_dir is not None:
        for entry in _read_dir(Path(data_dir).expanduser() / USER_CATALOG_DIRNAME):
            entries[entry.id] = entry
    return entries


def entries_for_profile(
    profile: str, data_dir: Path | None = None
) -> list[CatalogEntry]:
    """Every entry a profile names, in catalog order.

    An unknown profile raises rather than returning nothing — a typo that
    silently enables no services is the worst failure mode for this command.
    """
    if profile not in PROFILES:
        raise KeyError(profile)
    wanted = set(PROFILES[profile])
    return [e for e in load_entries(data_dir).values() if e.id in wanted]


def all_entries(data_dir: Path | None = None) -> list[CatalogEntry]:
    out = list(load_entries(data_dir).values())
    if PROFILES["all"]:
        wanted = set(PROFILES["all"])
        out.extend(e for e in load_entries(data_dir).values() if e.id in wanted)
    return out


# --------------------------------------------------------------------------
# generating a ServiceBase from an entry
# --------------------------------------------------------------------------


def _expand(template: str, data_dir: str, port: int) -> str:
    """Substitute {data_dir} and {port} in a catalog template.

    Deliberately not str.format on arbitrary input: a brace in an env var value
    would raise, and these values come from YAML the operator may not have
    written by hand.
    """
    return template.replace("{data_dir}", data_dir).replace("{port}", str(port))


def _service_class(entry: CatalogEntry) -> type:
    """Build a ServiceBase subclass for a generated entry.

    Kept as a closure over `entry` rather than a class body reading globals,
    because the portal and CLI both instantiate these and read `description`,
    `default_port` and `docker_image` as plain class attributes.
    """
    from .services.base import ServiceBase
    from .models import ServiceConfig

    class CatalogService(ServiceBase):
        name = entry.id
        description = entry.description
        default_port = entry.default_port or entry.container_port
        install_method = "docker"
        docker_image = entry.image
        requires_gpu = entry.needs_gpu
        puente_published = entry.puente_published

        def compose_fragment(
            self, config: ServiceConfig, data_dir: str
        ) -> dict[str, Any] | None:
            if not entry.managed:
                return None
            port = config.port or self.default_port

            fragment: dict[str, Any] = {
                "image": self.docker_image,
                "container_name": f"puente-{entry.id.replace('_', '-')}",
                "ports": [
                    f"{port}:{entry.container_port}",
                    *[_expand(p, data_dir, port) for p in entry.extra_ports],
                ],
                "restart": entry.restart,
            }

            if entry.build_context:
                fragment["build"] = {"context": entry.build_context}

            if entry.volumes:
                fragment["volumes"] = [
                    f"{_expand(host, data_dir, port)}:{container}"
                    for container, host in entry.volumes.items()
                ]

            env = {
                k: _expand(v, data_dir, port) for k, v in entry.environment.items()
            }
            env.update(config.environment)
            if env:
                fragment["environment"] = env

            if entry.extra_hosts:
                fragment["extra_hosts"] = list(entry.extra_hosts)

            return {entry.id.replace("_", "-"): fragment}

    CatalogService.__name__ = f"{entry.id.title().replace('_', '')}CatalogService"
    CatalogService.__doc__ = (
        f"{entry.description}\n\n"
        f"Generated from the service catalog (ADR0012) — not hand-written.\n"
        f"Upstream: {entry.repo or 'unknown'}"
    )
    return CatalogService
