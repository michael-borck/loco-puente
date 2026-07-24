"""Pydantic models for puente.yml configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field


class OllamaInstance(BaseModel):
    name: str = "primary"
    gpu: int | None = None
    port: int = 11434
    models: list[str] = Field(default_factory=lambda: ["llama3.1:8b-q4_k_m"])


class ProxyConfig(BaseModel):
    """Reverse-proxy exposure for a service. Attach to a service's `proxy:`
    block to have the Caddy service publish it at a public hostname.

    Auth policy mirrors the stack convention:
      * "none"   — app has its own accounts, or is public by design
      * "basic"  — UI tool with no built-in login (HTTP Basic)
      * "bearer" — API-only endpoint gated by a token
    """

    host: str  # public hostname, e.g. swarmui.locopuente.org
    auth: Literal["none", "basic", "bearer"] = "none"
    # For auth="bearer": name of the env var holding the token (read from the
    # Caddy container's environment). Keeps secrets out of the committed config.
    # A list names several env vars, any one of which is accepted — that's what
    # makes rotation possible: add the new token, migrate clients, drop the old.
    token_env: str | list[str] | None = None
    # For auth="basic": name of the basic-auth user group in CaddyConfig.users
    # to require. Defaults to the sole group when there's exactly one.
    basic_group: str | None = None
    # Optional upstream port override. Defaults to the service's own port. Set it
    # when a hostname fronts a different port than the service default, or when
    # two hostnames share one backend (e.g. a UI + an API on the same service).
    port: int | None = None
    # Optional upstream host override. Defaults to CaddyConfig.upstream_host.
    # Set it for a standalone host on a different machine (e.g. 192.168.20.3).
    upstream: str | None = None
    # Filename of an HTML page served (as 503) when the upstream is unreachable,
    # instead of a bare 502. Relative to the caddy data dir's `offline/`. Use it
    # for services that are DOWN ON PURPOSE some of the time — e.g. LibreChat's
    # lab windows — so visitors see "closed until your lab" rather than a
    # browser error. Also covers unplanned outages, which is a bonus, not the
    # main goal.
    offline_page: str | None = None

    def token_envs(self) -> list[str]:
        """`token_env` as a list, whether it was written as one name or several.

        Both the Caddyfile generator and the secret-collection pass go through
        here so a scalar and a single-item list can never render differently.
        """
        if self.token_env is None:
            return []
        if isinstance(self.token_env, str):
            return [self.token_env]
        return list(self.token_env)


class ServiceConfig(BaseModel):
    enabled: bool = True
    install_method: Literal["docker", "native", "external"] = "docker"
    port: int | None = None
    gpu: int | None = None
    managed: bool = True  # False = coexist with existing install
    environment: dict[str, str] = Field(default_factory=dict)
    review: bool = False  # True = surface in portal "Under Evaluation" section
    # Reverse-proxy exposure (Caddy service). A single block, or a list when the
    # service is published at several hostnames (e.g. a UI + an API route).
    proxy: ProxyConfig | list[ProxyConfig] | None = None


class AnythingLLMConfig(ServiceConfig):
    # Point at an EXISTING AnythingLLM storage dir to bring a hand-run install
    # under Puente without losing workspaces / embedded chatbots / vector data.
    # Defaults to Puente's own {data_dir}/anythingllm when None. Absolute path.
    storage_path: str | None = None
    # Set to the existing install's JWT_SECRET so embedded-chatbot embeds and
    # sessions keep working after migration. If None, AnythingLLM generates one.
    jwt_secret: str | None = None


class VoiceboxConfig(ServiceConfig):
    # Voicebox builds from a git context rather than a published image. Upstream
    # has no idle-model-unload, so an idle instance pins its weights (~5.6GB for
    # qwen-tts-1.7B) until the process restarts — most of an 8GB card. We build
    # from a fork carrying that patch (jamiepine/voicebox#889); once it merges,
    # drop build_ref from puente.yml to track upstream again.
    #
    # Format: "owner/repo@ref". Bare "owner/repo" builds that repo's default
    # branch. Set to None to build upstream jamiepine/voicebox.
    build_ref: str | None = None


class ChatterboxConfig(ServiceConfig):
    # Chatterbox TTS builds from a local checkout (its Dockerfile pins a tuned
    # CUDA/torch stack) — there is no image to pull. Set build_context to your
    # own Chatterbox-TTS-Server checkout; there is no sensible default, so
    # leaving it unset is an error rather than a path that only exists on one
    # machine. Superseded by voicebox, which bundles a chatterbox-tts engine.
    build_context: str | None = None
    # Optional HuggingFace token (some model pulls benefit from it).
    hf_token: str | None = None


class LibreChatConfig(ServiceConfig):
    # LibreChat needs MongoDB. When install_method is "external", point at an
    # existing LibreChat instead of running app+mongo locally.
    mongo_uri: str | None = None  # override the bundled mongo (e.g. external Atlas)
    # LibreChat refuses to boot without a JWT secret, and encrypts stored
    # provider credentials with CREDS_KEY/CREDS_IV. Persisted here so sessions
    # and saved credentials survive a container recreate.
    jwt_secret: str | None = None
    jwt_refresh_secret: str | None = None
    creds_key: str | None = None
    creds_iv: str | None = None
    # OpenAI-compatible base URL for the Ollama custom endpoint. Override to
    # point at a remote or other Ollama; default reaches the host's own instance.
    ollama_base_url: str | None = None
    # Models offered in the picker. When set, ONLY these are exposed and the
    # live fetch from Ollama is disabled — pulling a new model does not add it
    # here. Empty/unset = fetch whatever Ollama currently has.
    models: list[str] = Field(default_factory=list)
    # Model used to generate conversation titles. Defaults to the last entry in
    # `models` (pin the smallest one there). LibreChat's own default is
    # 'current_model', which makes titling contend with the live chat for the
    # GPU and abort — avoid unless the card has room for two loaded models.
    title_model: str | None = None
    # Context window forced on every Ollama request from LibreChat. Set it when
    # a model's default context is too large to load on the host GPU — the
    # failure is a hard runner abort at load time, not a graceful degradation,
    # so the model appears in the picker and then 500s on first use.
    num_ctx: int | None = None
    # Anthropic (Claude) endpoint. The key is read from the host environment —
    # named here, never stored here, so it stays out of git. `user_provided`
    # makes LibreChat prompt each user for their own key instead.
    anthropic_key_env: str | None = None
    anthropic_models: list[str] = Field(default_factory=list)
    # Email domains permitted to self-register. Enforced server-side in
    # AuthService (403 on mismatch), so it holds even with open registration.
    # Empty = any address may register.
    allowed_registration_domains: list[str] = Field(default_factory=list)
    # Resend (or any SMTP relay) for verification + password reset. Without
    # these, LibreChat auto-verifies new accounts and disables self-service
    # password reset. The API key belongs in the environment, not puente.yml.
    email_host: str | None = None
    email_port: int | None = None
    email_username: str | None = None
    email_password_env: str | None = None
    email_from: str | None = None
    email_from_name: str | None = None


class OllamaConfig(ServiceConfig):
    install_method: Literal["docker", "native", "external"] = "native"
    instances: list[OllamaInstance] = Field(
        default_factory=lambda: [OllamaInstance()]
    )


class SpeachesConfig(ServiceConfig):
    models: list[str] = Field(
        default_factory=lambda: [
            "Systran/faster-whisper-small",
            "speaches-ai/Kokoro-82M-v1.0-ONNX",
        ]
    )


class PortalConfig(ServiceConfig):
    host: str = "localhost"  # hostname/IP used in generated service URLs


class CaddyConfig(ServiceConfig):
    """The reverse proxy. When enabled, Caddy fronts every service that has a
    `proxy:` block, terminating TLS (automatic Let's Encrypt) and enforcing the
    per-service auth policy. Disable to bring your own proxy (NPM, Traefik, …).
    """

    install_method: Literal["docker", "native", "external"] = "docker"
    email: str = ""  # ACME contact for Let's Encrypt (recommended)
    # Basic-auth user groups: {group_name: {username: env_var_holding_bcrypt}}.
    # The generator emits `basic_auth { <user> {$<ENV>} }`, so the bcrypt hash
    # is read from the container environment, never committed.
    users: dict[str, dict[str, str]] = Field(default_factory=dict)
    # LAN address of the Docker host, used as the reverse_proxy upstream for
    # services running outside the puente network (native installs, other boxes).
    upstream_host: str = "host.docker.internal"
    # Standalone proxy hosts NOT tied to a puente service — anything you want
    # Caddy to front (personal sites, other machines, external APIs). Each needs
    # its own `port` (and usually `upstream`). Puente does not manage these
    # backends; a dead one simply 502s. This is config-as-code, not a manager:
    # you declare the boundary, Caddy serves it.
    proxy_hosts: list[ProxyConfig] = Field(default_factory=list)


class ComfyUIConfig(ServiceConfig):
    install_manager: bool = True  # clone ComfyUI-Manager into basedir/custom_nodes on pre_start
    install_sadtalker: bool = False  # patch Comfyui-SadTalker + download ~2.4GB weights on post_start
    install_wav2lip: bool = False  # install Wav2Lip + VideoHelperSuite nodes + ~416MB weight on post_start
    install_liveportrait: bool = False  # install LivePortraitKJ node + ~716MB models + insightface (non-commercial)
    liveportrait_animal: bool = False  # also fetch the ~520MB animal-trained LivePortrait models (needs install_liveportrait)
    install_wan_s2v: bool = False  # fetch ~22GB Wan2.2-S2V weights (nodes are in ComfyUI core); audio-driven video, works on NON-HUMAN characters


class StackConfig(BaseModel):
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    open_webui: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=3000)
    )
    speaches: SpeachesConfig = Field(
        default_factory=lambda: SpeachesConfig(port=8000, enabled=False)
    )
    comfyui: ComfyUIConfig = Field(
        default_factory=lambda: ComfyUIConfig(
            port=8188, install_method="docker", enabled=False
        )
    )
    searxng: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=8888)
    )
    vane: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=3005, enabled=False)
    )
    anythingllm: AnythingLLMConfig = Field(
        default_factory=lambda: AnythingLLMConfig(port=3001, enabled=False)
    )
    librechat: LibreChatConfig = Field(
        default_factory=lambda: LibreChatConfig(port=3080, enabled=False)
    )
    open_notebook: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=8502, enabled=False)
    )
    stirling_pdf: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=8089, enabled=False)
    )
    excalidraw: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=3333, enabled=False)
    )
    open_terminal: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=8100, enabled=False)
    )
    citesight: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=3010, enabled=False)
    )
    jupyter: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=8899, enabled=False)
    )
    deeptutor: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=3782, enabled=False)
    )
    musicgen: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=3000, enabled=False)
    )
    swarmui: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=7801, enabled=False)
    )
    fooocus: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=7865, enabled=False)
    )
    nodepad: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=3004, enabled=False)
    )
    # Graduated from evaluation — the active TTS. Still opt-in by default: it
    # wants a GPU and its first start compiles from source (see VoiceboxService).
    voicebox: VoiceboxConfig = Field(
        default_factory=lambda: VoiceboxConfig(port=17493, enabled=False, review=False)
    )
    chatterbox: ChatterboxConfig = Field(
        default_factory=lambda: ChatterboxConfig(port=8004, gpu=1, enabled=False, review=True)
    )
    glances: ServiceConfig = Field(
        default_factory=lambda: ServiceConfig(port=61208, enabled=False, review=True)
    )
    portal: PortalConfig = Field(
        default_factory=lambda: PortalConfig(port=8080, enabled=False)
    )
    caddy: CaddyConfig = Field(
        default_factory=lambda: CaddyConfig(enabled=False, managed=True)
    )


class PuenteConfig(BaseModel):
    data_dir: Path = Path("~/.puente")
    services: StackConfig = Field(default_factory=StackConfig)

    def resolved_data_dir(self) -> Path:
        return self.data_dir.expanduser()


CONFIG_FILE = "puente.yml"


def load_config(path: Path | None = None) -> PuenteConfig:
    """Load config from puente.yml, or return defaults if not found."""
    config_path = path or Path(CONFIG_FILE)
    if config_path.exists():
        raw = yaml.safe_load(config_path.read_text())
        return PuenteConfig.model_validate(raw or {})
    return PuenteConfig()


def save_config(config: PuenteConfig, path: Path | None = None) -> Path:
    """Write config to puente.yml."""
    config_path = path or Path(CONFIG_FILE)

    # Convert to dict, using aliases for yaml-friendly keys
    data = config.model_dump(mode="json")

    config_path.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
    return config_path
