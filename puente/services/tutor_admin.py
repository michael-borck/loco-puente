"""Tutor admin — narrow web UI over LibreChat's user database.

Off by default. Only useful alongside LibreChat, and it exposes account
administration, so it must be an explicit opt-in rather than something a new
install inherits.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from puente.models import ServiceConfig

from .base import ServiceBase

APP_SOURCE = Path(__file__).resolve().parent.parent / "tutor_admin" / "app.py"


class TutorAdminService(ServiceBase):
    name = "tutor_admin"
    description = "Tutor-facing LibreChat account admin"
    default_port = 8091
    install_method = "docker"
    # Purpose-built image: stock python:3.12-slim plus a PINNED pymongo. The app
    # itself is one stdlib file that pre_start copies into the bind mount on every
    # up, so the image holds no application code and code changes still ship
    # without a rebuild.
    #
    # This replaced a `pip install pymongo` in the container's entrypoint, which
    # meant the container needed outbound PyPI access to start, ran an arbitrary
    # version chosen that day, and failed in a way that looked like a hung app.
    docker_image = "ghcr.io/michael-borck/puente-tutor-admin:latest"
    puente_published = True
    requires_gpu = False

    def pre_start(self, config: ServiceConfig, data_dir: str) -> None:
        """Copy the app into the bind-mounted directory before the container starts.

        Same reasoning as librechat.yaml: the path must exist as a *file*, or
        Docker creates a directory there and the container starts with nothing
        to run. Rewritten every `up` so code changes ship without a rebuild.
        """
        target = Path(data_dir) / "tutor-admin"
        target.mkdir(parents=True, exist_ok=True)
        spool = target / "spool"
        spool.mkdir(exist_ok=True)
        # The container runs as root and writes the queue; the runner reads it
        # as the operator (it holds the Docker socket, so it must not be root).
        # Group-execute on the directory lets the runner traverse it — without
        # this the app's per-file chown is not enough to open anything.
        spool.chmod(0o750)
        app_file = target / "app.py"
        if app_file.is_dir():
            app_file.rmdir()
        app_file.write_text(APP_SOURCE.read_text())

    def compose_fragment(self, config: ServiceConfig, data_dir: str) -> dict[str, Any] | None:
        port = config.port or self.default_port
        env = dict(config.environment)
        env.setdefault("MONGO_URI", "mongodb://librechat-mongo:27017/LibreChat")
        env.setdefault("LIBRECHAT_URL", "http://librechat:3080")
        env.setdefault("AUDIT_LOG", "/data/audit.log")
        env.setdefault("SPOOL_DIR", "/data/spool")
        env.setdefault("PORT", str(port))
        # Who the runner runs as, so spooled files are readable by it.
        env.setdefault("SPOOL_UID", str(os.getuid()))
        env.setdefault("SPOOL_GID", str(os.getgid()))
        domains = getattr(config, "allowed_domains", None)
        if domains:
            env.setdefault("ALLOWED_DOMAINS", ",".join(domains))

        return {
            "tutor-admin": {
                "image": self.docker_image,
                # Fall back to building the image locally. Cheaper than the other
                # custom services — no torch, no CUDA, seconds rather than
                # minutes — so this is a genuinely usable escape hatch when the
                # published tag is missing, e.g. before the first publish or on
                # an architecture the amd64 image can't run.
                "build": {"context": "./dockerfiles/tutor-admin"},
                "container_name": "puente-tutor-admin",
                # 127.0.0.1 ON PURPOSE. This app performs no authentication of
                # its own — Caddy does it (proxy.auth: basic) and passes the
                # tutor's name through in X-Tutor-User. Publishing this port on
                # 0.0.0.0 would expose unauthenticated account administration
                # to the LAN. Caddy reaches it over the compose network.
                "ports": [f"127.0.0.1:{port}:{port}"],
                "volumes": [f"{data_dir}/tutor-admin:/data"],
                "environment": env,
                # No pip install: the dependency is baked into the image. The app
                # lives in the bind mount, so this path is rewritten on every up.
                "command": ["python", "/data/app.py"],
                # NO docker.sock. Creating accounts needs LibreChat's own npm
                # scripts, which need `docker exec`, which needs a writable
                # socket — root on the host, mounted into an internet-facing
                # service. Those two verbs are spooled to a host-side runner
                # instead (deploy/tutor-admin-runner.sh).
                "depends_on": ["librechat"],
                "restart": "unless-stopped",
            }
        }
