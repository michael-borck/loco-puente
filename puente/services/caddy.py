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


class CaddyService(ServiceBase):
    name = "caddy"
    description = "Reverse proxy + automatic TLS (fronts all proxied services)"
    default_port = 443
    install_method = "docker"
    docker_image = "caddy:2"
    requires_gpu = False

    def _secret_env_vars(self, config: PuenteConfig) -> list[str]:
        """Names of env vars the Caddyfile references and Caddy must receive:
        every bearer token_env, plus every basic-auth user's bcrypt env var —
        across both service-bound proxy blocks and standalone proxy_hosts.
        """
        names: set[str] = set()
        caddy = config.services.caddy
        service_blocks = (proxy for _s, _c, proxy in iter_proxied_services(config))
        for proxy in (*service_blocks, *caddy.proxy_hosts):
            if proxy.auth == "bearer" and proxy.token_env:
                names.add(proxy.token_env)
            elif proxy.auth == "basic":
                group = proxy.basic_group
                if group is None and len(caddy.users) == 1:
                    group = next(iter(caddy.users))
                for env_var in caddy.users.get(group, {}).values():
                    names.add(env_var)
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
        write_caddyfile(full, caddy_dir / "Caddyfile")

        # Materialize an .env for the container from the secrets present in the
        # host environment. Missing ones are skipped (Caddy will 401/deny rather
        # than crash) but reported so the operator knows to set them.
        env_path = caddy_dir / ".env"
        lines: list[str] = []
        missing: list[str] = []
        for var in self._secret_env_vars(full):
            val = os.environ.get(var)
            if val is None:
                missing.append(var)
                continue
            lines.append(f"{var}={val}")
        # Only rewrite .env if we resolved something; never clobber a
        # hand-maintained .env with an empty file.
        if lines:
            env_path.write_text("\n".join(lines) + "\n")
        elif not env_path.exists():
            env_path.write_text("")
        if missing:
            print(
                "  ⚠ Caddy: unset secret env vars (auth will deny until set): "
                + ", ".join(missing)
            )
