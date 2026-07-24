"""Caddy — the reverse proxy for the stack.

When enabled, Caddy fronts every service that declares a `proxy:` block in
puente.yml: it terminates TLS (automatic Let's Encrypt) and enforces the
per-service auth policy (none / basic / bearer). The Caddyfile is generated
from the same config, so there's no second source of truth to drift.

Secrets (bcrypt hashes for basic-auth, bearer tokens) are NOT written into the
Caddyfile — the generator emits `{$ENV_VAR}` placeholders and this service
passes the values through from the environment, so puente.yml stays committable.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from puente.caddy import iter_proxied_services, write_caddyfile
from puente.models import PuenteConfig, ServiceConfig

from .base import ServiceBase


def _read_env_file(path: Path) -> dict[str, str]:
    """Parse a docker-compose `.env` into {name: raw_value}.

    Values are returned exactly as stored — still `$$`-escaped — so a merge can
    write them back untouched. Blank lines and `#` comments are skipped; a line
    with no `=` is ignored rather than raising, since a corrupt or hand-edited
    file should not block a deploy.
    """
    if not path.exists():
        return {}
    env: dict[str, str] = {}
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        # split on the FIRST "=" only: bcrypt hashes and base64 tokens can
        # contain "=" in the value.
        key, _, value = stripped.partition("=")
        env[key.strip()] = value
    return env


class CaddyService(ServiceBase):
    name = "caddy"
    description = "Reverse proxy + automatic TLS (fronts all proxied services)"
    default_port = 443
    install_method = "docker"
    docker_image = "caddy:2"
    requires_gpu = False

    def _secret_env_vars(self, config: PuenteConfig) -> list[str]:
        """Names of env vars the Caddyfile references and Caddy must receive:
        every bearer token_env (a host may name several), plus every basic-auth
        user's bcrypt env var — across both service-bound proxy blocks and
        standalone proxy_hosts.
        """
        names: set[str] = set()
        caddy = config.services.caddy
        service_blocks = (proxy for _s, _c, proxy in iter_proxied_services(config))
        for proxy in (*service_blocks, *caddy.proxy_hosts):
            if proxy.auth == "bearer":
                names.update(proxy.token_envs())
            elif proxy.auth == "basic":
                group = proxy.basic_group
                if group is None and len(caddy.users) == 1:
                    group = next(iter(caddy.users))
                for value in caddy.users.get(group, {}).values():
                    # Inline bcrypt hashes ("$2...") are not env vars — skip them.
                    if not value.startswith("$2"):
                        names.add(value)
        return sorted(names)

    def compose_fragment(
        self, config: ServiceConfig, data_dir: str
    ) -> dict[str, Any] | None:
        caddy_dir = f"{data_dir}/caddy"
        # Ensure the dir and a .env exist now, so a standalone `docker compose`
        # (without a prior pre_start) doesn't fail on a missing env_file.
        # pre_start overwrites .env with the real, freshly-resolved secrets.
        Path(caddy_dir).mkdir(parents=True, exist_ok=True)
        env_path = Path(caddy_dir) / ".env"
        if not env_path.exists():
            env_path.write_text("")

        fragment: dict[str, Any] = {
            "caddy": {
                "image": self.docker_image,
                "container_name": "puente-caddy",
                "ports": ["80:80", "443:443", "443:443/udp"],
                "volumes": [
                    f"{caddy_dir}/Caddyfile:/etc/caddy/Caddyfile:ro",
                    f"{caddy_dir}/data:/data",
                    f"{caddy_dir}/config:/config",
                    # Static pages served when an upstream is down; see
                    # ProxyConfig.offline_page. Mounted unconditionally so
                    # adding a page later needs no container recreate.
                    f"{caddy_dir}/offline:/srv/offline:ro",
                ],
                # host.docker.internal must resolve to the LAN gateway so Caddy
                # can reach native / off-network upstreams. compose.py rewrites
                # host-gateway to the puente bridge gateway.
                "extra_hosts": ["host.docker.internal:host-gateway"],
                "env_file": [f"{caddy_dir}/.env"],
                "restart": "unless-stopped",
            }
        }
        return fragment

    def pre_start(self, config: ServiceConfig, data_dir: str) -> None:
        """Regenerate the Caddyfile from the live puente.yml before starting.

        Loading the full config here (rather than trusting the partial
        ServiceConfig) lets the generator see every service's proxy block.
        """
        from puente.models import load_config

        full = load_config()
        caddy_dir = Path(data_dir) / "caddy"
        caddy_dir.mkdir(parents=True, exist_ok=True)
        # Bind source for the offline pages. Must exist before the container
        # starts or Docker creates it as root-owned, which then can't be
        # written without sudo (same trap as the /basedir dirs).
        (caddy_dir / "offline").mkdir(parents=True, exist_ok=True)
        write_caddyfile(full, caddy_dir / "Caddyfile")

        # Materialize an .env for the container from the secrets present in the
        # host environment, MERGED over whatever .env already holds.
        #
        # Merging (rather than replacing) is what makes it safe to run with only
        # some secrets exported: `export OLLAMA_TOKEN_2=... && puente up caddy`
        # used to rewrite .env with just that one var and silently drop every
        # other token, breaking auth on hosts the operator never touched.
        # A var still set in the environment wins; anything else is carried
        # forward. Missing-everywhere vars are reported, not written.
        env_path = caddy_dir / ".env"
        existing = _read_env_file(env_path)
        resolved: dict[str, str] = {}
        missing: list[str] = []
        for var in self._secret_env_vars(full):
            val = os.environ.get(var)
            if val is not None:
                # Docker Compose interpolates $ in env_file values, which mangles
                # bcrypt hashes ($2a$14$...). Escape $ as $$ so Compose passes the
                # value through literally. Values carried over from the existing
                # file are already escaped — re-escaping them would double the $
                # on every run, so only freshly-read env vars go through this.
                resolved[var] = val.replace("$", "$$")
            elif var in existing:
                resolved[var] = existing[var]
            else:
                missing.append(var)

        # Preserve unrecognized keys (hand-added vars, secrets for a host that
        # is temporarily commented out) so a merge never loses operator data.
        merged = {**existing, **resolved}
        if merged:
            env_path.write_text(
                "\n".join(f"{k}={v}" for k, v in sorted(merged.items())) + "\n"
            )
        elif not env_path.exists():
            env_path.write_text("")
        if missing:
            print(
                "  ⚠ Caddy: unset secret env vars (auth will deny until set): "
                + ", ".join(missing)
            )
