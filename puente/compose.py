"""Docker Compose file generation from service fragments."""

from __future__ import annotations

from pathlib import Path

import yaml

from puente.models import PuenteConfig
from puente.services import ALL_SERVICES


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

    return {"services": services} if services else {}


def write_compose(config: PuenteConfig, output_path: Path | None = None) -> Path:
    """Generate and write docker-compose.yml."""
    compose_data = generate_compose(config)
    path = output_path or config.resolved_data_dir() / "docker-compose.yml"
    path.parent.mkdir(parents=True, exist_ok=True)

    path.write_text(yaml.dump(compose_data, default_flow_style=False, sort_keys=False))
    return path
