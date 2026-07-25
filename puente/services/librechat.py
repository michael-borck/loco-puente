"""LibreChat — multi-provider chat UI (app + MongoDB)."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase


class LibreChatService(ServiceBase):
    name = "librechat"
    description = "Multi-provider chat UI (frontier-alternative front end)"
    default_port = 3080
    install_method = "docker"
    docker_image = "ghcr.io/danny-avila/librechat:latest"
    requires_gpu = False

    def _render_config(self, config: ServiceConfig) -> str:
        """Render librechat.yaml. Single source of truth for both the file
        written in pre_start and the digest stamped into the compose spec."""
        ollama_base = getattr(config, "ollama_base_url", None) or "http://host.docker.internal:11434/v1"
        # An explicit list pins the picker to exactly those models; without one
        # we fetch whatever Ollama currently serves. `default` must be non-empty
        # either way (schema requirement), so it doubles as the allow-list.
        allowed = list(getattr(config, "models", None) or [])
        fetch = "false" if allowed else "true"
        if not allowed:
            allowed = ["llama3.1:8b-instruct-q4_K_M"]  # seed only; fetch replaces it
        models_yaml = "".join(f"          - '{m}'\n" for m in allowed)

        # Falls back to the last pinned model only as a last resort — `models`
        # is in picker order, not size order, so set title_model explicitly to
        # get a small one. 'current_model' is LibreChat's default and is
        # deliberately not used here — see titleModel below.
        title_model = getattr(config, "title_model", None) or allowed[-1]

        # Ollama options forced on every request to this endpoint, merged into
        # the request body LibreChat sends. Two keys are wired here:
        #
        # num_ctx — does NOT reliably control context size. It was tried as a
        # fix for a model whose declared context was too large to load, and
        # Ollama still sized its KV cache from the model's own declared
        # context — the load kept failing with the pre-addParams memory figure.
        # To cap context, bake it into the model instead:
        #   printf 'FROM <model>\nPARAMETER num_ctx 16384\n' > m.Modelfile
        #   ollama create <model>-16k -f m.Modelfile
        # and pin the variant in `models`.
        #
        # disable_thinking — turns reasoning OFF on thinking-capable models
        # (gemma4, qwen3.5). Emitted as OpenAI's `reasoning_effort: none`, NOT
        # Ollama's `think: false`: this endpoint is the OpenAI-compatible /v1
        # route, which has no `think` field, but Ollama's /v1 shim maps
        # reasoning_effort:none to think:false internally (verified against
        # Ollama 0.32.3 — think:false only exists on the native /api/chat, and
        # `PARAMETER think false` is not a valid Modelfile param). Applies to
        # every model on this endpoint; harmless for non-thinking models.
        num_ctx = getattr(config, "num_ctx", None)
        disable_thinking = bool(getattr(config, "disable_thinking", None))

        def endpoint(name: str, *, thinking_off: bool) -> str:
            """One custom-endpoint block. All endpoints serve the same `models`
            from the same Ollama, differing only in whether reasoning_effort is
            forced off — the (thinking) companion, when present, exists purely
            so students can pick the same model with thinking on vs off."""
            params: list[str] = []
            if num_ctx:
                params.append(f"        num_ctx: {num_ctx}\n")
            if thinking_off:
                params.append("        reasoning_effort: none\n")
            addparams_yaml = "      addParams:\n" + "".join(params) if params else ""
            return (
                f"    - name: '{name}'\n"
                f"      baseURL: '{ollama_base}'\n"
                "      apiKey: '${OLLAMA_API_KEY}'\n"
                "      models:\n"
                "        # fetch:false + an explicit default = the picker shows only\n"
                "        # these. fetch:true would overwrite the list from Ollama.\n"
                f"        fetch: {fetch}\n"
                "        default:\n"
                f"{models_yaml}"
                f"{addparams_yaml}"
                "      titleConvo: true\n"
                # Titling fires a *second* inference alongside the live chat. With
                # 'current_model' both hit the same large model and contend for the
                # card — the title request loses and aborts ("This operation was
                # aborted"), so chats stay untitled. Point this at a small model so
                # titling never competes with the conversation.
                f"      titleModel: '{title_model}'\n"
                f"      modelDisplayLabel: '{name}'\n"
            )

        # Primary endpoint reflects disable_thinking. When both disable_thinking
        # AND thinking_comparison are on, add a companion "Ollama (thinking)"
        # that leaves reasoning ON, so the picker offers e.g. Ollama → gemma4:12b
        # (off) vs Ollama (thinking) → gemma4:12b (on). Same weights, same loaded
        # copy — no extra VRAM. Only meaningful when thinking is otherwise off;
        # with thinking already on, a second identical endpoint is redundant.
        endpoints_yaml = endpoint("Ollama", thinking_off=disable_thinking)
        if disable_thinking and getattr(config, "thinking_comparison", None):
            endpoints_yaml += endpoint("Ollama (thinking)", thinking_off=False)

        # Enforced in AuthService.registerUser — a non-matching address gets a
        # 403 at signup. This is the real gate on an open registration page;
        # it works with or without email configured.
        domains = list(getattr(config, "allowed_registration_domains", None) or [])
        registration_yaml = ""
        if domains:
            registration_yaml = "registration:\n  allowedDomains:\n" + "".join(
                f"    - '{d}'\n" for d in domains
            )

        return (
            "# Generated by puente — edits will be overwritten on `puente up`.\n"
            "version: 1.3.13\n"
            "cache: true\n"
            f"{registration_yaml}"
            "endpoints:\n"
            "  custom:\n"
            f"{endpoints_yaml}"
        )

    def _write_env_file(self, config: ServiceConfig, data_dir: str) -> None:
        """Materialize secrets compose must not interpolate itself.

        Written every `puente up` from the host environment, mirroring how the
        caddy service handles its tokens. Always created (possibly empty) so a
        standalone `docker compose up` doesn't fail on a missing env_file.
        """
        env_dir = Path(data_dir) / "librechat"
        env_dir.mkdir(parents=True, exist_ok=True)
        lines: list[str] = []

        if getattr(config, "email_host", None):
            var = getattr(config, "email_password_env", None) or "RESEND_API_KEY"
            value = os.environ.get(var)
            if value:
                # $ would be interpolated by compose; $$ passes it through.
                lines.append(f"EMAIL_PASSWORD={value.replace('$', '$$')}")
            else:
                print(
                    f"  ⚠ LibreChat: {var} not set in the environment — SMTP will "
                    f"fail (530) and verification/reset emails will not send. "
                    f"Export it where `puente up` runs, not just in .zshrc."
                )

        (env_dir / ".env").write_text("\n".join(lines) + ("\n" if lines else ""))

    def pre_start(self, config: ServiceConfig, data_dir: str) -> None:
        """Seed librechat.yaml before the container starts.

        The file is bind-mounted, so it must exist as a *file* first — Docker
        would otherwise create a directory at that path and LibreChat would log
        "Config file YAML format is invalid" and fall back to defaults.
        Rewritten every up so endpoint changes take effect; user edits belong
        in puente.yml, not here.
        """
        self._write_env_file(config, data_dir)

        target = Path(data_dir) / "librechat" / "librechat.yaml"
        target.parent.mkdir(parents=True, exist_ok=True)
        # ensure_volume_dirs() runs before this hook and mkdir -p's every bind
        # source, so on a fresh install the path already exists as a directory.
        # Clear it so the write below produces a file.
        if target.is_dir():
            target.rmdir()
        target.write_text(self._render_config(config))

    def compose_volumes(self, config: ServiceConfig) -> dict[str, dict[str, Any]]:
        return {"librechat-mongo": {}, "librechat-images": {}, "librechat-logs": {}}

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        # external = point LibreChat elsewhere; nothing runs here.
        if getattr(config, "install_method", "docker") == "external":
            return None

        port = config.port or self.default_port
        env = dict(config.environment)
        # Bundled mongo unless the config overrides it (e.g. external Atlas).
        mongo_uri = getattr(config, "mongo_uri", None) or "mongodb://librechat-mongo:27017/LibreChat"
        env.setdefault("MONGO_URI", mongo_uri)
        # LibreChat exits at startup ("JwtStrategy requires a secret or key")
        # unless these are set. Values come from puente.yml so they stay stable
        # across recreates — regenerating them would invalidate every session
        # and make stored provider credentials undecryptable.
        for env_key, attr in (
            ("JWT_SECRET", "jwt_secret"),
            ("JWT_REFRESH_SECRET", "jwt_refresh_secret"),
            ("CREDS_KEY", "creds_key"),
            ("CREDS_IV", "creds_iv"),
        ):
            value = getattr(config, attr, None)
            if value:
                env.setdefault(env_key, value)
        # LibreChat 0.8.x defaults registration OFF. Open signup is the
        # deliberate choice here; the first account to register becomes ADMIN.
        # Override per-install via `environment: {ALLOW_REGISTRATION: 'false'}`.
        env.setdefault("ALLOW_REGISTRATION", "true")
        # Ollama is wired as a *custom endpoint* (see pre_start / librechat.yaml)
        # rather than via OPENAI_REVERSE_PROXY. The reverse-proxy route reuses the
        # built-in OpenAI endpoint, which carries a hardcoded model list, so the
        # picker shows gpt-* names instead of the locally installed Ollama models.
        # A custom endpoint with `models.fetch: true` pulls the real list from
        # /v1/models at load time. Placeholder key: Ollama needs no auth, but
        # LibreChat requires the field to be non-empty.
        env.setdefault("OLLAMA_API_KEY", "ollama")
        env.setdefault("CONFIG_PATH", "/app/librechat.yaml")

        # Anthropic endpoint. LibreChat has native Claude support, so this is a
        # first-class endpoint rather than a custom OpenAI-compatible one.
        # ANTHROPIC_MODELS pins the picker to the listed models.
        key_env = getattr(config, "anthropic_key_env", None)
        if key_env:
            # `user_provided` is a literal sentinel, not an env var name.
            env.setdefault(
                "ANTHROPIC_API_KEY",
                key_env if key_env == "user_provided" else f"${{{key_env}}}",
            )
            claude_models = list(getattr(config, "anthropic_models", None) or [])
            if claude_models:
                env.setdefault("ANTHROPIC_MODELS", ",".join(claude_models))

        # Public URL, used to build links in outgoing email. Without it
        # LibreChat falls back to http://localhost:3080, so a verification link
        # is unusable for anyone but someone sitting at the host. Derived from
        # the proxy host so it tracks the public hostname automatically.
        proxy = getattr(config, "proxy", None)
        proxy_host = getattr(proxy, "host", None) if proxy else None
        if proxy_host:
            public_url = f"https://{proxy_host}"
            env.setdefault("DOMAIN_CLIENT", public_url)
            env.setdefault("DOMAIN_SERVER", public_url)

        # SMTP. When EMAIL_HOST is set LibreChat sends a verification link on
        # signup and enables self-service password reset; without it, accounts
        # are auto-verified and reset is disabled entirely.
        email_host = getattr(config, "email_host", None)
        if email_host:
            env.setdefault("EMAIL_HOST", email_host)
            env.setdefault("EMAIL_PORT", str(getattr(config, "email_port", None) or 587))
            env.setdefault("EMAIL_USERNAME", getattr(config, "email_username", None) or "resend")
            env.setdefault("EMAIL_FROM", getattr(config, "email_from", None) or "")
            env.setdefault("EMAIL_FROM_NAME", getattr(config, "email_from_name", None) or "LibreChat")
            # Password comes from the host environment so the secret stays out
            # of puente.yml. NOT emitted as a ${VAR} placeholder: compose
            # interpolates those from ITS OWN environment, which is empty when
            # `puente up` runs from cron or systemd (the key lives in .zshrc,
            # an interactive-shell-only file). The container then gets an empty
            # EMAIL_PASSWORD, and LibreChat's sendEmail only attaches SMTP auth
            # when username AND password are both truthy — so it connects
            # unauthenticated and Resend answers "530 Authentication Required",
            # with the failure swallowed behind an optimistic "Verification
            # link issued" log line. pre_start writes the resolved value to an
            # env_file instead; see _write_env_file.
            pw_env = getattr(config, "email_password_env", None) or "RESEND_API_KEY"
            self._password_env_var = pw_env
            # Password reset has its own switch — configuring SMTP is not enough.
            # Only meaningful with email working, hence nested here.
            env.setdefault("ALLOW_PASSWORD_RESET", "true")

        # librechat.yaml is bind-mounted and only read at boot, so editing it
        # is invisible to compose — it would report "Running" and leave the old
        # config live. Stamping its hash into a label makes the container spec
        # change, so compose recreates and the new config actually takes effect.
        config_digest = hashlib.sha256(
            self._render_config(config).encode()
        ).hexdigest()[:12]

        fragment: dict[str, Any] = {
            "librechat": {
                "image": self.docker_image,
                "container_name": "puente-librechat",
                "ports": [f"{port}:3080"],
                "environment": env,
                "labels": {"puente.config-digest": config_digest},
                "extra_hosts": ["host.docker.internal:host-gateway"],
                # Secrets that must reach the container verbatim rather than via
                # compose interpolation — see _write_env_file.
                "env_file": [f"{data_dir}/librechat/.env"],
                "volumes": [
                    "librechat-images:/app/client/public/images",
                    "librechat-logs:/app/api/logs",
                    f"{data_dir}/librechat/librechat.yaml:/app/librechat.yaml:ro",
                ],
                "depends_on": ["librechat-mongo"],
                "restart": "unless-stopped",
            }
        }
        # Only run the bundled mongo when not using an external one.
        if not getattr(config, "mongo_uri", None):
            fragment["librechat-mongo"] = {
                "image": "mongo:7",
                "container_name": "puente-librechat-mongo",
                "command": "mongod --noauth",
                "volumes": ["librechat-mongo:/data/db"],
                "restart": "unless-stopped",
            }

        return fragment
