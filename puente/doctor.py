"""Environment checks for `puente doctor`.

Every check here is strictly *read-only*. It reports what it finds and prints the
command that would fix it, but never runs one. That separation is deliberate:
this is the first thing a new operator runs, and it must be safe to run against a
live box mid-incident.

Two rules shape the design:

  * **Never install, never mutate.** No `sudo`, no writes, no daemon restarts.
    A driver or Docker upgrade is a real risk to every running service (see
    docs/host-setup.md §1) and is the operator's decision, not ours.
  * **Say what would fix it.** A check that only reports "GPU unavailable" leaves
    the reader guessing. Each failure carries the remediation as text.
"""

from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
from dataclasses import dataclass
from typing import Any, Literal

from .models import PuenteConfig
from .compose import resolve_network

Status = Literal["pass", "warn", "fail", "skip"]

#: Exit codes for `puente doctor`, so it is usable as a CI / monitoring gate.
EXIT_OK = 0
EXIT_WARN = 0  # Warnings are advisory; only hard failures gate a pipeline.
EXIT_FAIL = 1


@dataclass
class Check:
    """One environment check.

    `fix` is a *recommendation to print*, never something to execute.
    """

    name: str
    status: Status
    detail: str = ""
    fix: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "fix": self.fix,
        }


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _run(cmd: list[str], timeout: int = 10) -> tuple[int, str]:
    """Run a command, returning (returncode, stdout+stderr). Never raises."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except FileNotFoundError:
        return 127, ""
    except (subprocess.TimeoutExpired, OSError):
        return 124, ""


def _port_free(port: int, host: str = "0.0.0.0") -> bool:
    """True if nothing is listening on `port`.

    Binding 0.0.0.0 mirrors what a container publishing the port needs: a
    listener on 127.0.0.1 alone still blocks a later `docker compose up`.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind((host, port))
        except OSError:
            return False
    return True


# --------------------------------------------------------------------------
# checks
# --------------------------------------------------------------------------


def check_docker() -> list[Check]:
    """Docker Engine present, and Compose available as the v2 plugin.

    Puente generates a v2-style compose file (`deploy.resources.reservations`,
    top-level `networks`), which the legacy `docker-compose` v1 binary rejects.
    """
    checks: list[Check] = []

    if shutil.which("docker") is None:
        return [
            Check(
                "docker",
                "fail",
                "docker not found on PATH",
                "Install Docker Engine: https://docs.docker.com/engine/install/",
            )
        ]

    rc, out = _run(["docker", "version", "--format", "{{.Server.Version}}"])
    if rc != 0:
        checks.append(
            Check(
                "docker",
                "fail",
                "docker CLI present but the daemon is not responding",
                "Start Docker and confirm your user can reach it (`sudo systemctl start docker`).",
            )
        )
    else:
        checks.append(Check("docker", "pass", f"Engine {out}"))

    # v2 plugin — note this is `docker compose`, not `docker-compose`.
    rc_v2, out_v2 = _run(["docker", "compose", "version", "--short"])
    if rc_v2 != 0:
        legacy = shutil.which("docker-compose")
        if legacy:
            checks.append(
                Check(
                    "docker-compose-v2",
                    "fail",
                    "only the legacy v1 `docker-compose` binary is available",
                    "Install the Compose v2 plugin (apt: docker-compose-plugin). "
                    "Puente's generated file uses v2 syntax.",
                )
            )
        else:
            checks.append(
                Check(
                    "docker-compose-v2",
                    "fail",
                    "Compose v2 plugin not found",
                    "Install the Compose v2 plugin (apt: docker-compose-plugin).",
                )
            )
    else:
        checks.append(Check("docker-compose-v2", "pass", f"Compose {out_v2}"))

    return checks


def check_nvidia_runtime() -> list[Check]:
    """The NVIDIA container runtime is configured as a Docker default runtime.

    Every GPU service in the stack relies on `driver: nvidia` resolving. Puente
    never sets `runtime: nvidia` per service, so it depends entirely on the
    daemon having the toolkit registered as the default. If it isn't, containers
    start successfully and then fail to see any GPU — which reads as "the service
    is broken" rather than "the host is misconfigured".

    We diagnose only. Installing the toolkit, or editing daemon.json and
    restarting Docker (which stops every running container), is the operator's
    call.
    """
    checks: list[Check] = []

    if shutil.which("nvidia-smi") is None:
        return [
            Check(
                "nvidia",
                "skip",
                "no NVIDIA GPU on this host",
                "GPU services are unavailable. Fine for CPU-only deployments.",
            )
        ]

    rc, out = _run(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"])
    if rc != 0:
        checks.append(
            Check(
                "nvidia",
                "fail",
                "nvidia-smi present but returned an error",
                "Check `nvidia-smi` on its own; the driver may need a reboot after install.",
            )
        )
    else:
        driver = out.splitlines()[0].strip() if out else "unknown"
        checks.append(Check("nvidia", "pass", f"driver {driver}"))

    # Does the daemon actually hand GPUs to containers?
    rc, out = _run(
        ["docker", "info", "--format", "{{json .Runtimes}} {{.DefaultRuntime}}"]
    )
    if rc != 0:
        checks.append(
            Check(
                "nvidia-container-runtime",
                "skip",
                "could not read docker info (daemon not reachable?)",
            )
        )
        return checks

    parts = out.split(" ", 1)
    runtimes = parts[0] if parts else "{}"
    default_runtime = parts[1].strip() if len(parts) > 1 else ""

    if "nvidia" in runtimes:
        # The daemon can register nvidia as an *additional* runtime while leaving
        # `runc` as the default. That is fine: compose's `driver: nvidia`
        # selects the runtime explicitly per device request, it does not rely on
        # it being the default. Report both facts rather than implying the
        # default matters when it doesn't.
        detail = "nvidia runtime registered"
        if default_runtime not in ("", "nvidia"):
            detail += f" (default runtime: {default_runtime})"
        checks.append(Check("nvidia-container-runtime", "pass", detail))
    else:
        checks.append(
            Check(
                "nvidia-container-runtime",
                "fail",
                "the nvidia runtime is not registered with Docker",
                "Install nvidia-container-toolkit, then run "
                "`sudo nvidia-ctk runtime configure --runtime=docker && sudo systemctl restart docker`. "
                "Note: restarting Docker stops running containers.",
            )
        )

    return checks


def check_gpu_pins(config: PuenteConfig) -> list[Check]:
    """Validate every `gpu:` pin in the config against real hardware.

    A pin is a UUID (stable) or a legacy integer index (not stable — indices are
    reassigned when cards are reordered or the box re-enumerates, which silently
    loads a workload onto the wrong card; see
    deploy/ollama-classroom/10-classroom.conf for that post-mortem).

    Legacy index pins get a warning rather than a pass, because they work today
    and will quietly stop meaning what they mean after the next hardware change.
    """
    from .gpu import detect_gpus, resolve_gpu

    pins: list[tuple[str, str]] = []
    ollama = config.services.ollama
    if ollama.enabled:
        # A pin on a NATIVE ollama is inert. `install_method: native` means the
        # service has no compose representation, so no `deploy:` block is ever
        # emitted for it and the pin in puente.yml is never read by anything.
        # The real pin lives in a systemd drop-in, which this function cannot
        # see. Validating it anyway is worse than not validating it: it reports
        # a GPU as accounted for when the running process may be pinned
        # somewhere else entirely. That is not hypothetical — puente.yml said the
        # 3090 while 10-classroom.conf pinned the 4060 Ti, and this check
        # passed both.
        if ollama.install_method != "native":
            for inst in ollama.instances:
                if inst.gpu is not None:
                    pins.append((f"ollama/{inst.name}", str(inst.gpu)))
    # llama.cpp pins per instance too — one server, one model, one card.
    llama = getattr(config.services, "llama_cpp", None)
    if llama is not None and llama.enabled:
        for inst in llama.instances:
            if inst.gpu is not None:
                pins.append((f"llama_cpp/{inst.name}", str(inst.gpu)))
    for name, svc_cls in _service_classes().items():
        svc = getattr(config.services, name, None)
        if svc is None or not getattr(svc, "enabled", False):
            continue
        if getattr(svc_cls, "requires_gpu", False) and getattr(svc, "gpu", None) is not None:
            pins.append((name, str(svc.gpu)))

    if not pins:
        return [
            Check(
                "gpu-pins",
                "pass",
                "no services pin a specific GPU (they will share all cards)",
            ),
            *_native_pin_checks(config),
        ]

    gpus = detect_gpus()
    inventory = ", ".join(
        f"{g.index}={g.name} ({g.vram_gb:.0f}GB){' ' + g.short_uuid() if g.uuid else ''}"
        for g in gpus
    )
    native_warnings = _native_pin_checks(config)

    if not gpus:
        return [
            Check(
                "gpu-pins",
                "fail",
                f"{len(pins)} service(s) pin a GPU but none was detected: "
                + ", ".join(f"{n}=gpu:{p}" for n, p in pins),
                "Check the NVIDIA driver, or clear the `gpu:` pins to let services share.",
            ),
            *native_warnings,
        ]

    unresolved = [(n, p) for n, p in pins if resolve_gpu(p, gpus) is None]
    if unresolved:
        return [
            Check(
                "gpu-pins",
                "fail",
                f"pin(s) reference a GPU that doesn't exist: "
                + ", ".join(f"{n}=gpu:{p}" for n, p in unresolved)
                + f". Present: {inventory}",
                "Correct the `gpu:` value in puente.yml. `puente gpu` prints the "
                "UUID to use — prefer it over an index.",
            ),
            *native_warnings,
        ]

    # Everything resolved. Distinguish UUID pins from index pins.
    by_index = [(n, p) for n, p in pins if p.isdigit()]
    detail = ", ".join(f"{n}=gpu:{p}" for n, p in pins)

    if by_index:
        return [
            Check(
                "gpu-pins",
                "pass",
                f"{detail} — all valid. {inventory}",
            ),
            Check(
                "gpu-index-pins",
                "warn",
                f"{len(by_index)} pin(s) use an integer index: "
                + ", ".join(f"{n}=gpu:{p}" for n, p in by_index),
                "Indices are reassigned when cards are reordered or the host "
                "re-enumerates, so these can silently land on a different card. "
                "Replace with the UUID from `puente gpu`.",
            ),
            *native_warnings,
        ]

    return [
        Check("gpu-pins", "pass", f"{detail} — all valid. {inventory}"),
        *native_warnings,
    ]


def _native_pin_checks(config: PuenteConfig) -> list[Check]:
    """Warn when a native service carries a `gpu:` pin that nothing will apply.

    A native install has no compose fragment, so `gpu:` on it is inert — the
    real pin lives in a systemd drop-in, which puente cannot see or validate.
    The failure this catches is silent and was live here: puente.yml pinned the
    3090, 10-classroom.conf pinned the 4060 Ti, and the pin check passed both
    because it only checked that the UUID exists.
    """
    ollama = config.services.ollama
    if not ollama.enabled or ollama.install_method != "native":
        return []
    pinned = [i.name for i in ollama.instances if i.gpu is not None]
    if not pinned:
        return []
    return [
        Check(
            "gpu-pins-native",
            "warn",
            f"ollama/{', '.join(pinned)}: gpu: pin is ignored for a native install",
            "puente only emits a GPU reservation for containerised services. The "
            "pin that actually applies is in the systemd drop-in "
            "(/etc/systemd/system/<svc>.service.d/). Check it with "
            "`systemctl cat ollama`, then set gpu: null here so there is one "
            "source of truth.",
        )
    ]


def check_ports(config: PuenteConfig) -> list[Check]:
    """Ports needed by enabled services are free.

    Only meaningful before the stack is up — once containers are running their
    own ports are in use by definition, which is why this is advisory.
    """
    needed: set[int] = set()
    if config.services.caddy.enabled:
        needed.update({80, 443})

    busy = sorted(p for p in needed if not _port_free(p))
    if not busy:
        return [
            Check(
                "ports",
                "pass",
                "proxy ports free" if needed else "no privileged ports required",
            )
        ]
    return [
        Check(
            "ports",
            "warn",
            f"port(s) already in use: {', '.join(str(p) for p in busy)}",
            "Stop whatever holds them, or disable the caddy service. Expected to be "
            "in use if the stack is already running.",
        )
    ]


def check_subnet(config: PuenteConfig) -> list[Check]:
    """The stack's bridge subnet doesn't collide with an existing route.

    The default range (172.28.0.0/24) is pinned for UFW rule stability and so
    `host.docker.internal` resolves on Linux, but that range is claimed by
    plenty of VPN and k8s setups, which would silently misroute rather than
    error. Overridable via `network:` in puente.yml since 0.1.3.
    """
    net = resolve_network(config)
    subnet, bridge = net["subnet"], net["name"]
    prefix = subnet.split("/")[0]

    rc, out = _run(["ip", "route", "show"])
    if rc != 0:
        return [Check("network-subnet", "skip", "`ip route` unavailable (non-Linux?)")]

    # Ignore routes on our OWN bridge — when the stack is up, the pinned
    # subnet is in the routing table by definition. Flagging that would make the
    # check fail on every healthy running install. Only foreign routes matter.
    foreign = [
        line for line in out.splitlines() if prefix in line and bridge not in line
    ]
    if foreign:
        return [
            Check(
                "network-subnet",
                "fail",
                f"{subnet} is claimed by another route: {foreign[0].strip()}",
                f"Set a free range in puente.yml, e.g.\n"
                f"        network:\n"
                f"          subnet: 10.44.0.0/24\n"
                f"          name: {bridge}\n"
                f"then `puente up` (the gateway is derived from the subnet).",
            )
        ]

    # Our own bridge holding the subnet is the healthy, expected case.
    own = bridge in out
    return [
        Check(
            "network-subnet",
            "pass",
            f"{subnet} free" if not own else f"{subnet} held by {bridge}",
        )
    ]


def check_secrets(config: PuenteConfig) -> list[Check]:
    """Every secret a proxy block needs is actually available.

    Per ADR 0002 secrets are resolved at `up` time from the environment and
    never read from a shell profile. That has a consequence worth spelling out,
    because getting it wrong makes this check cry wolf on a working stack:

    **The host environment is not where the value lives afterwards.** `puente up`
    copies resolved values into `{data_dir}/caddy/.env` and Caddy reads that file
    at runtime. Anyone who runs `puente doctor` later — from a fresh shell, from
    cron, in a new terminal — has none of those vars set, so an
    environment-only check reports every bearer token as "unset → the route will
    401" while the route is in fact serving authenticated traffic.

    So a var counts as resolved if it is in the environment **or** in the
    generated `.env`. The Caddyfile itself is no help here: it holds only
    `{$VAR}` placeholders, never values, which is the whole point of ADR 0002.
    """
    wanted: set[str] = set()
    caddy = config.services.caddy
    for _name, env_var in (caddy.users or {}).items():
        wanted.update(env_var.values())

    from .caddy import iter_proxied_services

    for _svc_name, _svc_config, proxy in iter_proxied_services(config):
        wanted.update(proxy.token_envs())

    # `proxy_hosts` fronts services puente doesn't manage (external boxes, Plex,
    # …) but can carry the same auth policy, so its tokens count too.
    for proxy in (caddy.proxy_hosts or []):
        wanted.update(proxy.token_envs())

    if not wanted:
        return [Check("secrets", "pass", "no proxy secrets required")]

    # What Caddy actually reads. Present only once `puente up caddy` has run.
    from .services.caddy import _read_env_file

    resolved_env = _read_env_file(config.resolved_data_dir() / "caddy" / ".env")

    def _where(var: str) -> str | None:
        if os.environ.get(var):
            return "environment"
        if resolved_env.get(var):
            return "caddy .env"
        return None

    missing = sorted(v for v in wanted if not _where(v))
    if not missing:
        n_env = sum(1 for v in wanted if _where(v) == "environment")
        n_file = len(wanted) - n_env
        where = (
            "environment"
            if not n_file
            else f"{n_env} environment, {n_file} caddy .env"
        )
        return [Check("secrets", "pass", f"{len(wanted)} secret(s) resolved ({where})")]

    # A `$2...`-prefixed value is a bcrypt hash written inline rather than an env
    # var name. The Caddyfile generator accepts both (see caddy.py), so an inline
    # hash is not "missing" — but it IS a secret committed to the config file,
    # and this repo is public. Flag it as its own problem so it isn't lost among
    # genuinely-unset vars.
    inline = [v for v in missing if v.startswith("$2")]
    unset = [v for v in missing if not v.startswith("$2")]

    out: list[Check] = []
    if unset:
        out.append(
            Check(
                "secrets",
                "warn",
                "unset: " + ", ".join(unset),
                "Export these before `puente up caddy`, or the corresponding proxy "
                "routes will answer 401. A var that was set at a previous `up` is "
                "already in {data_dir}/caddy/.env and is NOT listed here — this is "
                "only naming vars that have never been resolved anywhere. Do not put "
                "them in a shell profile; see ADR 0002.",
            )
        )
    if inline:
        out.append(
            Check(
                "secrets-inline",
                "warn",
                f"{len(inline)} bcrypt hash(es) committed inline in puente.yml",
                "Move the hash to a variable name (e.g. `users: {ui: {alice: ALICE_HASH}}`) "
                "and supply the value via the environment. This repo is public — a "
                "committed hash cannot be un-leaked.",
            )
        )
    return out


def check_image_arch(config: PuenteConfig) -> list[Check]:
    """Puente's own images match the host architecture.

    `build-images.yml` publishes `linux/amd64` only — every current target is
    x86. An arm64 host (the M3 Ultra in the Phase 2 roadmap) cannot run them, and
    `docker pull` fails with a platform error that reads like a network problem.
    Reported here instead, with the build fallback named as the way out.

    Skipped entirely when there is no GPU to reason about from the host side.
    """
    from .gpu import detect_gpus

    arch = platform.machine()
    services = [
        (name, cls.docker_image)
        for name, cls in _service_classes().items()
        if getattr(cls, "puente_published", False)
    ]
    if not services:
        return [Check("image-arch", "pass", "no puente-published images in use")]

    if arch not in ("x86_64", "amd64", "aarch64", "arm64"):
        return [
            Check(
                "image-arch",
                "skip",
                f"unrecognised host architecture {arch!r}; skipping arch check",
            )
        ]

    if arch in ("x86_64", "amd64"):
        return [
            Check(
                "image-arch",
                "pass",
                f"host is {arch}; puente images are linux/amd64",
            )
        ]

    # arm64 host. The services carry a `build:` fallback, so a source build
    # would work — slowly, and for swarmui/fooocus/nodepad that build clones
    # upstream at build time, so it tracks moving branches.
    names = ", ".join(n for n, _ in services)
    return [
        Check(
            "image-arch",
            "warn",
            f"host is {arch} but puente images are linux/amd64; "
            f"affected: {names}",
            "Either build on this host (the services carry a `build:` fallback), "
            "or extend .github/workflows/build-images.yml with `platforms: "
            "linux/amd64,linux/arm64`. Note CUDA is unavailable on Apple silicon, "
            "so GPU services need the MPS/CPU path regardless.",
        )
    ]


def check_portal_links(config: PuenteConfig) -> list[Check]:
    """Every link on the generated portal points somewhere this stack owns.

    The portal is the student-facing launcher, so a wrong link sends people to
    someone else's machine. Historically it fell back to a hardcoded map of
    *.locopuente.org hostnames for any service without a `proxy:` block; that
    fallback is gone (see portal.py), but a stale `proxy:` block can still name a
    host this deployment no longer owns, so the rendered links are checked
    against the config's own declared hostnames.
    """
    hostnames = {proxy.host for _svc, _cfg, proxy in _iter_proxies(config)}

    try:
        from .portal import FOREIGN_PROXY_HOSTS, build_views

        views = build_views(config, "localhost")
    except Exception as exc:  # a template bug shouldn't fail the whole doctor
        return [Check("portal-links", "warn", f"could not render portal: {exc}")]

    links = [svc.url for v in views for s in v.sections for svc in s.services]
    foreign = sorted(
        u for u in links if u.startswith("http://localhost") is False
        and any(h in u for h in FOREIGN_PROXY_HOSTS)
        and u.split("/")[2] not in hostnames
    )

    if foreign:
        return [
            Check(
                "portal-links",
                "warn",
                f"{len(foreign)} portal link(s) point at a hostname this stack doesn't declare: "
                + ", ".join(foreign[:4]),
                "Check those services' `proxy:` blocks in puente.yml. Students clicking "
                "these are sent off-box.",
            )
        ]
    return [
        Check("portal-links", "pass", f"{len(links)} portal link(s), all self-hosted")
    ]


def _iter_proxies(config: PuenteConfig):
    """Every proxy block in the config, as (svc_name, svc_config, proxy)."""
    from .caddy import iter_proxied_services

    return iter_proxied_services(config)


def check_tools() -> list[Check]:
    """Optional host binaries some deployments rely on."""
    checks: list[Check] = []
    for tool, why in (
        ("jq", "required by deploy/tutor-admin-runner.sh"),
        ("curl", "used by native Ollama install"),
    ):
        if shutil.which(tool):
            checks.append(Check(f"tool-{tool}", "pass", "present"))
        else:
            checks.append(
                Check(f"tool-{tool}", "warn", f"not found — {why}", f"apt install {tool}")
            )
    return checks


def _service_classes() -> dict:
    from .services import ALL_SERVICES

    return ALL_SERVICES


# --------------------------------------------------------------------------
# orchestration
# --------------------------------------------------------------------------


def run_checks(config: PuenteConfig | None = None) -> list[Check]:
    """Run every check. Read-only; safe on a live host."""
    from .models import PuenteConfig as _PC

    cfg = config or _PC()
    checks: list[Check] = []
    checks += check_docker()
    checks += check_nvidia_runtime()
    checks += check_gpu_pins(cfg)
    checks += check_subnet(cfg)
    checks += check_ports(cfg)
    checks += check_secrets(cfg)
    checks += check_image_arch(cfg)
    checks += check_portal_links(cfg)
    checks += check_tools()
    return checks


def exit_code(checks: list[Check]) -> int:
    return EXIT_FAIL if any(c.status == "fail" for c in checks) else EXIT_OK


def report_dict(checks: list[Check]) -> dict[str, Any]:
    """Machine-readable result, for `--json`."""
    return {
        "checks": [c.to_dict() for c in checks],
        "summary": {
            s: sum(1 for c in checks if c.status == s)
            for s in ("pass", "warn", "fail", "skip")
        },
        "exit_code": exit_code(checks),
    }