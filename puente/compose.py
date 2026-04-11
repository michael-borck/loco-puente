"""Docker Compose file generation from service fragments."""

from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from puente.models import PuenteConfig
from puente.services import ALL_SERVICES

# Stable bridge for all puente containers.
#
# We pin the bridge name, subnet, and gateway so that:
#   1. UFW can allow traffic on a stable interface name: `sudo ufw allow in on puente0`
#   2. `host.docker.internal` can be mapped to a reachable gateway IP on Linux,
#      where Docker's built-in `host-gateway` alias only resolves to docker0
#      (172.17.0.1) and is unreachable from custom bridge networks.
PUENTE_NETWORK_BRIDGE_NAME = "puente0"
PUENTE_NETWORK_SUBNET = "172.28.0.0/24"
PUENTE_NETWORK_GATEWAY = "172.28.0.1"


def _rewrite_host_gateway(services: dict) -> None:
    """Replace `host-gateway` in extra_hosts with the puente network gateway.

    Docker's `host-gateway` alias works on Docker Desktop but on Linux it always
    points at the docker0 bridge IP, which is unreachable from containers on a
    custom bridge network. Substituting the puente network's own gateway IP
    ensures `host.docker.internal` resolves to a reachable address regardless.
    """
    for svc in services.values():
        extra_hosts = svc.get("extra_hosts")
        if not extra_hosts:
            continue
        svc["extra_hosts"] = [
            h.replace("host-gateway", PUENTE_NETWORK_GATEWAY) for h in extra_hosts
        ]


def generate_compose(config: PuenteConfig) -> dict:
    """Collect compose fragments from all enabled Docker services."""
    data_dir = str(config.resolved_data_dir())
    services: dict = {}

    for svc_name, svc_class in ALL_SERVICES.items():
        svc_config = getattr(config.services, svc_name, None)
        if svc_config is None or not svc_config.enabled:
            continue
        if not svc_config.managed:
            continue
        if svc_config.install_method != "docker":
            continue

        svc = svc_class()
        fragment = svc.compose_fragment(svc_config, data_dir)
        if fragment:
            services.update(fragment)

    if not services:
        return {}

    _rewrite_host_gateway(services)

    return {
        "services": services,
        "networks": {
            "default": {
                "driver": "bridge",
                "driver_opts": {
                    "com.docker.network.bridge.name": PUENTE_NETWORK_BRIDGE_NAME,
                },
                "ipam": {
                    "config": [
                        {
                            "subnet": PUENTE_NETWORK_SUBNET,
                            "gateway": PUENTE_NETWORK_GATEWAY,
                        }
                    ]
                },
            }
        },
    }


def _install_dockerfiles(target_root: Path) -> None:
    """Mirror the bundled puente/dockerfiles tree into ``{data_dir}/dockerfiles``.

    Services that build from source (musicgen, swarmui, fooocus) reference
    ``./dockerfiles/<name>`` as their compose build context — that path is
    relative to docker-compose.yml, which lives in ``data_dir``. Copying the
    bundled Dockerfiles here on every ``write_compose`` call keeps them in
    sync with whatever version of puente is installed without requiring the
    user to think about it.
    """
    source_root = Path(__file__).parent / "dockerfiles"
    if not source_root.exists():
        return
    target_root.mkdir(parents=True, exist_ok=True)
    for entry in source_root.iterdir():
        if not entry.is_dir():
            continue
        dest = target_root / entry.name
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(entry, dest)


def write_compose(config: PuenteConfig, output_path: Path | None = None) -> Path:
    """Generate and write docker-compose.yml."""
    compose_data = generate_compose(config)
    path = output_path or config.resolved_data_dir() / "docker-compose.yml"
    path.parent.mkdir(parents=True, exist_ok=True)

    _install_dockerfiles(path.parent / "dockerfiles")

    path.write_text(yaml.dump(compose_data, default_flow_style=False, sort_keys=False))
    return path
