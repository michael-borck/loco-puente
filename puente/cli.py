"""Puente CLI — local AI stack orchestrator."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from puente import __version__
from puente.catalog import PROFILES, all_entries, entries_for_profile
from puente.compose import ensure_volume_dirs, generate_compose, write_compose
from puente.detect import detect_all
from puente.doctor import Check, exit_code, report_dict, run_checks
from puente.gpu import detect_gpus, print_gpu_table, resolve_gpu, suggest_gpu_assignment
from puente.models import (
    ConfigNotFound,
    OllamaConfig,
    OllamaInstance,
    PuenteConfig,
    ServiceConfig,
    StackConfig,
    find_config_path,
    load_config,
    save_config,
)
from puente.services import ALL_SERVICES

app = typer.Typer(
    name="puente",
    help="Local AI stack orchestrator — privacy-first, pick-and-choose, upstream-only.",
    no_args_is_help=True,
)
console = Console()

#: Absolute path of the config in use, set by the callback below so every command
#: -- including ones that never call `_require_config` -- can report where it is.
#: Populated by find_config_path, which searches upward from the cwd.
_active_config: Path | None = None


@app.callback()
def main(
    config: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to puente.yml (default: search upward from the current directory)",
    ),
):
    """Locate the stack config once, up front, for every command."""
    global _active_config
    if config is not None:
        resolved = config.expanduser()
        if not resolved.exists():
            console.print(f"[red]No config at {resolved}[/red]")
            raise typer.Exit(1)
        _active_config = resolved
    else:
        _active_config = find_config_path()

    # Record the resolved path for the systemd units we generate, so they point
    # at the same config this invocation used rather than guessing a directory.
    if _active_config is not None:
        try:
            cfg = load_config(_active_config)
            data = cfg.resolved_data_dir()
            (data / "config-path").write_text(f"{_active_config.resolve()}\n")
        except Exception:
            # Recording the path is a convenience for `puente install-units`;
            # never let it stop the command the user actually asked for.
            pass


# -- Service display names for pretty printing --------------------------------

DISPLAY_NAMES = {
    "ollama": "Ollama",
    "localai": "LocalAI",
    "open_webui": "Open WebUI",
    "speaches": "Speaches",
    "comfyui": "ComfyUI",
    "searxng": "SearXNG",
    "vane": "Vane (AI Search)",
    "anythingllm": "AnythingLLM",
    "open_notebook": "Open Notebook AI",
    "stirling_pdf": "Stirling PDF",
    "presenton": "Presenton",
    "excalidraw": "Excalidraw",
    "open_terminal": "Open Terminal",
    "citesight": "CiteSight",
    "jupyter": "JupyterLab",
    "deeptutor": "DeepTutor",
    "musicgen": "MusicGen",
    "swarmui": "SwarmUI",
    "fooocus": "Fooocus",
}


# -- Sidecars -----------------------------------------------------------------
# Some services own an extra compose service (a "sidecar") that shares their
# lifecycle but has a distinct compose-service name. A scoped `puente up <svc>`
# passes only <svc> to `docker compose up`, so without this map the sidecar is
# skipped — and if it is then hand-started it ends up NOT compose-managed, so a
# later bare `docker compose up` hits `Conflict. container name already in use`.
# Mapping the parent to its sidecar service names keeps them started/stopped
# together and compose-owned. Keys/values are compose-service names (hyphens).
SIDECARS = {
    "portal": ["portal-gpu-stats"],
}


def _scoped_compose_names(service: str) -> list[str]:
    """Compose-service name(s) for a scoped up/down: the service plus any
    sidecars it owns, so a sidecar is never left un-managed."""
    compose_name = service.replace("_", "-")
    return [compose_name, *SIDECARS.get(compose_name, [])]


# -- init ----------------------------------------------------------------------


@app.command()
def init():
    """Interactive setup — detect hardware, pick services, write puente.yml."""
    console.print(f"\n[bold]Puente v{__version__}[/bold] — Local AI Stack Orchestrator\n")

    # 1. Detect GPUs
    console.print("[bold cyan]Step 1:[/bold cyan] Detecting GPUs...")
    gpus = detect_gpus()
    if gpus:
        print_gpu_table(gpus)
        assignment = suggest_gpu_assignment(gpus)
    else:
        console.print("[yellow]No NVIDIA GPUs detected. GPU services will be disabled.[/yellow]")
        assignment = {}

    # 2. Scan for existing installs
    console.print("\n[bold cyan]Step 2:[/bold cyan] Scanning for existing installs...")
    existing = detect_all()
    if existing:
        for ex in existing:
            console.print(f"  Found [green]{ex.service}[/green] ({ex.method}: {ex.detail})")
    else:
        console.print("  No existing installs detected.")

    # 3. Select services
    console.print("\n[bold cyan]Step 3:[/bold cyan] Select services to include\n")

    # Reference stack defaults
    reference_enabled = {"ollama", "open_webui", "searxng"}
    if gpus:
        reference_enabled.add("speaches")

    services_config = {}
    for svc_name, svc_class in ALL_SERVICES.items():
        svc = svc_class()
        default_on = svc_name in reference_enabled
        is_existing = any(e.service == svc_name.replace("_", "-") or e.service == svc_name for e in existing)

        if is_existing:
            marker = " (already installed)"
        else:
            marker = ""

        if svc.requires_gpu and not gpus:
            console.print(f"  [dim]{DISPLAY_NAMES.get(svc_name, svc_name)} — skipped (no GPU)[/dim]")
            services_config[svc_name] = ServiceConfig(
                enabled=False,
                install_method=svc.install_method,
                port=svc.default_port,
            )
            continue

        prompt = f"  Include {DISPLAY_NAMES.get(svc_name, svc_name)}?{marker}"
        enabled = typer.confirm(prompt, default=default_on)

        managed = True
        if enabled and is_existing:
            managed = typer.confirm(
                f"    Let puente manage {DISPLAY_NAMES.get(svc_name, svc_name)}? (No = coexist with existing)",
                default=False,
            )

        gpu_id = None
        if enabled and svc.requires_gpu and assignment:
            if svc_name == "speaches":
                gpu_id = assignment.get("voice")
            elif svc_name in ("comfyui",):
                gpu_id = assignment.get("images")

        services_config[svc_name] = ServiceConfig(
            enabled=enabled,
            install_method=svc.install_method,
            port=svc.default_port,
            gpu=gpu_id,
            managed=managed,
        )

    # Build OllamaConfig specially (supports multiple instances)
    ollama_svc = services_config.pop("ollama", ServiceConfig(enabled=True))
    instances = []
    if ollama_svc.enabled:
        instances.append(
            OllamaInstance(
                name="primary",
                gpu=assignment.get("primary_llm"),
                port=11434,
            )
        )
        if len(gpus) > 1:
            add_secondary = typer.confirm("  Add secondary Ollama instance on second GPU?", default=True)
            if add_secondary:
                instances.append(
                    OllamaInstance(
                        name="secondary",
                        gpu=assignment.get("secondary_llm"),
                        port=11435,
                    )
                )

    ollama_config = OllamaConfig(
        enabled=ollama_svc.enabled,
        managed=ollama_svc.managed,
        instances=instances,
    )

    # 4. Authentication
    console.print("\n[bold cyan]Step 4:[/bold cyan] Authentication\n")

    enable_auth = typer.confirm("  Enable user authentication?", default=True)

    if enable_auth and "open_webui" in services_config and services_config["open_webui"].enabled:
        services_config["open_webui"].environment["WEBUI_AUTH"] = "true"
        console.print("    Open WebUI: auth enabled (first signup = admin)")
    elif "open_webui" in services_config and services_config["open_webui"].enabled:
        services_config["open_webui"].environment["WEBUI_AUTH"] = "false"
        console.print("    Open WebUI: auth disabled (demo mode)")

    # 5. Build config
    stack = StackConfig(ollama=ollama_config, **services_config)
    config = PuenteConfig(services=stack)

    # 6. Write config + compose
    config_path = save_config(config)
    console.print(f"\n[green]Wrote {config_path}[/green]")

    compose_data = generate_compose(config)
    if compose_data.get("services"):
        compose_path = write_compose(config)
        console.print(f"[green]Wrote {compose_path}[/green]")

    # 7. Summary
    console.print("\n[bold]Stack summary:[/bold]")
    _print_config_summary(config)

    console.print(f"\nRun [bold cyan]puente up[/bold cyan] to start your stack.")


# -- install -------------------------------------------------------------------


@app.command()
def install():
    """Install native services (Ollama, models, ComfyUI) and pull Docker images."""
    config = _require_config()
    data_dir = config.resolved_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)

    # -- Ollama --
    if config.services.ollama.enabled and config.services.ollama.managed:
        from puente.detect import check_binary, check_systemd

        if check_binary("ollama"):
            console.print("[green]Ollama already installed[/green]")
        else:
            console.print("[cyan]Installing Ollama...[/cyan]")
            result = subprocess.run(
                ["bash", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
                capture_output=False,
            )
            if result.returncode == 0:
                console.print("[green]Ollama installed[/green]")
            else:
                console.print("[red]Ollama install failed[/red]")

        # Ensure Ollama is running before pulling models
        if not check_systemd("ollama"):
            console.print("[cyan]Starting Ollama service...[/cyan]")
            subprocess.run(["sudo", "systemctl", "enable", "--now", "ollama"], capture_output=False)

        # Pull models
        for inst in config.services.ollama.instances:
            for model in inst.models:
                console.print(f"[cyan]Pulling model: {model}...[/cyan]")
                subprocess.run(["ollama", "pull", model], capture_output=False)

    # -- Docker images (pre-pull) --
    console.print("\n[cyan]Pulling Docker images...[/cyan]")
    for svc_name, svc_class in ALL_SERVICES.items():
        svc_config = getattr(config.services, svc_name, None)
        if svc_config is None or not svc_config.enabled:
            continue
        if svc_config.install_method != "docker":
            continue

        svc = svc_class()
        if svc.docker_image:
            console.print(f"  Pulling {svc.docker_image}...")
            subprocess.run(["docker", "pull", svc.docker_image], capture_output=False)

    # -- SearXNG config (needs JSON format enabled for Vane) --
    if config.services.searxng.enabled:
        searxng_dir = data_dir / "searxng"
        settings_file = searxng_dir / "settings.yml"
        if not settings_file.exists():
            console.print("[cyan]Creating SearXNG config (JSON format enabled)...[/cyan]")
            searxng_dir.mkdir(parents=True, exist_ok=True)
            # The engines block is not decoration. Measured 2026-10-17 on the
            # PoC box: with upstream defaults only, a general query returned
            # ZERO results — aol/brave/duckduckgo/startpage/karmasearch were
            # all CAPTCHA'd, rate-limited or suspended from this IP, and those
            # are the engines the default set picks. google/bing/wikipedia
            # answered fine when forced via ?engines=. Open WebUI queries with
            # format=json and no engines param, so it hits exactly the dead
            # default set — "web search failed" with nothing visibly wrong.
            # Force-enabling the three reliable ones keeps the default query
            # path alive; the captchas on the others clear within the hour and
            # they rejoin on their own.
            settings_file.write_text(
                "use_default_settings: true\n"
                "\n"
                "search:\n"
                "  formats:\n"
                "    - html\n"
                "    - json\n"
                "\n"
                "server:\n"
                "  secret_key: puente-searxng-secret\n"
                "  limiter: false\n"
                "\n"
                "engines:\n"
                "  - name: google\n"
                "    disabled: false\n"
                "  - name: bing\n"
                "    disabled: false\n"
                "  - name: wikipedia\n"
                "    disabled: false\n"
            )
            console.print("[green]SearXNG config written[/green]")

    # -- Generate docker-compose.yml --
    compose_path = data_dir / "docker-compose.yml"
    write_compose(config, compose_path)
    console.print(f"\n[green]docker-compose.yml written to {compose_path}[/green]")

    console.print("\n[bold]Install complete.[/bold] Run [bold cyan]puente up[/bold cyan] to start.")


# -- up / down -----------------------------------------------------------------


@app.command()
def up(service: str | None = typer.Argument(None, help="Start a specific service, or all if omitted")):
    """Start the stack (or a specific service)."""
    config = _require_config()
    data_dir = config.resolved_data_dir()
    compose_path = data_dir / "docker-compose.yml"

    # Validate GPU pins before generating anything. A pin that no longer matches
    # real hardware either fails the compose file or — worse — resolves to a
    # different card, putting a 12B model on the wrong GPU. Catching it here
    # gives a named message instead of a mid-deploy failure. Skipped for a
    # scoped `up <svc>` that isn't GPU-backed, so a CPU-only service can still
    # be started while the host is being repaired.
    _warn_invalid_gpu_pins(config, scoped=service)

    # Always regenerate so upstream changes to compose.py / service fragments
    # are picked up without requiring users to manually delete the file.
    compose_data = generate_compose(config)
    ensure_volume_dirs(compose_data)
    write_compose(config, compose_path)

    # Keep the portal launcher page in sync with current config.
    if config.services.portal.enabled:
        from puente.portal import write_portal

        write_portal(config, config.services.portal.host)

    _ufw_warning_if_needed()

    # Per-service pre-start hooks (e.g. config file pre-seeding) — must
    # run before docker compose so any files land in mounted volumes
    # before the container's first read.
    for svc_name, svc_class in ALL_SERVICES.items():
        if service and svc_name != service:
            continue
        svc_config = getattr(config.services, svc_name, None)
        if svc_config is None or not svc_config.enabled:
            continue
        if svc_config.install_method != "docker":
            continue
        svc_class().pre_start(svc_config, str(data_dir))

    # Start Docker services
    if compose_path.exists() and compose_path.stat().st_size > 20:
        cmd = ["docker", "compose", "-f", str(compose_path), "up", "-d"]
        # Ollama is the only non-Docker service; everything else (including
        # ComfyUI) is a regular compose service and can be scoped normally.
        if service and service != "ollama":
            cmd.extend(_scoped_compose_names(service))
        console.print(f"[cyan]Starting Docker services...[/cyan]")
        subprocess.run(cmd)

    # Per-service post-start hooks (e.g. model pre-pull)
    for svc_name, svc_class in ALL_SERVICES.items():
        if service and svc_name != service:
            continue
        svc_config = getattr(config.services, svc_name, None)
        if svc_config is None or not svc_config.enabled:
            continue
        if svc_config.install_method != "docker":
            continue
        svc_class().post_start(svc_config, str(data_dir))

    console.print("[green]Done.[/green] Run [bold]puente status[/bold] to check.")


@app.command()
def down(service: str | None = typer.Argument(None, help="Stop a specific service, or all if omitted")):
    """Stop the stack (or a specific service)."""
    config = _require_config()
    compose_path = config.resolved_data_dir() / "docker-compose.yml"

    if compose_path.exists():
        cmd = ["docker", "compose", "-f", str(compose_path), "down"]
        # Ollama is the only non-Docker service; everything else (including
        # ComfyUI) is a regular compose service and can be scoped normally.
        if service and service != "ollama":
            cmd.append("--remove-orphans")
            cmd.extend(_scoped_compose_names(service))
        console.print(f"[cyan]Stopping Docker services...[/cyan]")
        subprocess.run(cmd)

    console.print("[green]Done.[/green]")


# -- enable / disable ----------------------------------------------------------


def _resolve_service(service: str) -> str:
    """Validate and normalize a service name argument."""
    normalized = service.lower().replace("-", "_")
    if normalized not in ALL_SERVICES:
        valid = ", ".join(sorted(ALL_SERVICES.keys()))
        console.print(f"[red]Unknown service:[/red] {service}")
        console.print(f"[dim]Valid services:[/dim] {valid}")
        raise typer.Exit(1)
    if normalized == "ollama":
        console.print(
            "[yellow]Ollama uses a multi-instance config — edit puente.yml or run "
            "puente init to reconfigure it.[/yellow]"
        )
        raise typer.Exit(1)
    return normalized


@app.command()
def enable(
    service: str = typer.Argument(..., help="Service name, or @profile to enable a group"),
    port: int | None = typer.Option(None, help="Override the service port"),
    gpu: str | None = typer.Option(
        None, help="GPU to pin to: a UUID (preferred) or an index. See `puente gpu`"
    ),
    review: bool = typer.Option(
        False,
        "--review",
        help="Mark the service as Under Evaluation in the portal",
    ),
):
    """Enable a service in puente.yml without touching other config.

    `@profile` enables a whole group instead — `puente enable @office` turns on
    the CPU-only document and diagramming tools in one go, rather than three
    edits to puente.yml.
    """
    if service.startswith("@"):
        return _enable_profile(service[1:])

    name = _resolve_service(service)
    config = _require_config()
    svc_config = getattr(config.services, name)
    svc_config.enabled = True
    if port is not None:
        svc_config.port = port
    if gpu is not None:
        resolved = resolve_gpu(gpu)
        if resolved is None:
            console.print(
                f"[red]No GPU matches {gpu!r}.[/red] Run [bold]puente gpu[/bold] for the "
                f"available cards.\n  The pin is still written, so you can fix puente.yml "
                f"by hand."
            )
        else:
            console.print(f"  GPU: {resolved.name}")
        svc_config.gpu = gpu
    if review:
        svc_config.review = True
    save_config(config)
    write_compose(config)
    console.print(f"[green]Enabled[/green] {DISPLAY_NAMES.get(name, name)} in puente.yml")
    console.print(f"  Run [bold cyan]puente up {name}[/bold cyan] to start it.")


def _enable_profile(profile: str) -> None:
    """Enable every catalog entry a profile names.

    A typo must not silently enable nothing, so an unknown profile exits 1 with
    the list of real ones rather than reporting success.
    """
    config = _require_config()
    try:
        entries = entries_for_profile(profile, config.resolved_data_dir())
    except KeyError:
        console.print(f"[red]Unknown profile:[/red] {profile}")
        console.print(f"[dim]Available:[/dim] {', '.join(sorted(PROFILES))}")
        raise typer.Exit(1)

    enabled: list[str] = []
    skipped: list[str] = []
    for entry in entries:
        svc_config = getattr(config.services, entry.id, None)
        if svc_config is None:
            skipped.append(f"{entry.id} (no config block)")
            continue
        if svc_config.enabled:
            skipped.append(f"{entry.id} (already on)")
            continue
        svc_config.enabled = True
        enabled.append(DISPLAY_NAMES.get(entry.id, entry.name))

    save_config(config)
    write_compose(config)
    console.print(f"[green]Enabled profile [bold]{profile}[/bold]:[/green] "
                  f"{', '.join(enabled) if enabled else 'nothing'}")
    for s in skipped:
        console.print(f"  [dim]skipped {s}[/dim]")
    if enabled:
        console.print("  Run [bold cyan]puente up[/bold cyan] to start them.")


@app.command()
def catalog(
    profile: str | None = typer.Argument(None, help="Show only this profile's entries"),
    available: bool = typer.Option(
        True, "--available/--all", help="Off: include entries already enabled"
    ),
):
    """List what the catalog declares.

    The catalog is how a third-party image joins the stack without Puente
    shipping a service class for it (ADR0012). Everything here is opt-in.
    """
    config = load_config()
    entries = (
        entries_for_profile(profile, config.resolved_data_dir())
        if profile
        else all_entries(config.resolved_data_dir())
    )
    if not entries:
        console.print(f"[red]Unknown profile:[/red] {profile}")
        console.print(f"[dim]Available:[/dim] {', '.join(sorted(PROFILES))}")
        raise typer.Exit(1)

    table = Table(title=f"Service catalog{f' — {profile}' if profile else ''}")
    table.add_column("Service", style="bold")
    table.add_column("Provides")
    table.add_column("VRAM")
    table.add_column("Profiles")
    table.add_column("On", justify="center")

    for entry in sorted(entries, key=lambda e: e.id):
        svc_config = getattr(config.services, entry.id, None)
        on = bool(svc_config and svc_config.enabled)
        if not available and on:
            continue
        vram = "—" if entry.needs_vram_mb == 0 else f"{entry.needs_vram_mb // 1024} GB"
        table.add_row(
            entry.name,
            ", ".join(entry.provides) or "—",
            vram,
            ", ".join(entry.profiles) or "—",
            "[green]yes[/green]" if on else "[dim]no[/dim]",
        )

    console.print(table)
    if not profile:
        console.print(
            "[dim]All catalog entries are opt-in. Enable one with[/dim] "
            "[cyan]puente enable <name>[/cyan][dim], or a group with[/dim] "
            "[cyan]puente enable @<profile>[/cyan][dim].[/dim]"
        )


@app.command()
def disable(
    service: str = typer.Argument(..., help="Service name (e.g. musicgen, swarmui)"),
):
    """Disable a service in puente.yml without touching other config."""
    name = _resolve_service(service)
    config = _require_config()
    svc_config = getattr(config.services, name)
    svc_config.enabled = False
    save_config(config)
    write_compose(config)
    console.print(f"[green]Disabled[/green] {DISPLAY_NAMES.get(name, name)} in puente.yml")
    console.print(f"  Run [bold cyan]puente down {name}[/bold cyan] to stop the container.")


# -- status --------------------------------------------------------------------


@app.command()
def status():
    """Show the status of all enabled services."""
    config = _require_config()

    table = Table(title="Puente Stack Status")
    table.add_column("Service", style="bold")
    table.add_column("Port", justify="right")
    table.add_column("Method")
    table.add_column("GPU", justify="right")
    table.add_column("Status")
    table.add_column("Managed")

    for svc_name, svc_class in ALL_SERVICES.items():
        # Skip generic Ollama row — instances are shown separately below
        if svc_name == "ollama":
            continue

        svc_config = getattr(config.services, svc_name, None)
        if svc_config is None or not svc_config.enabled:
            continue

        svc = svc_class()
        st = svc.status(svc_config)
        status_str = "[green]running[/green]" if st.running else "[red]stopped[/red]"
        gpu_str = str(svc_config.gpu) if svc_config.gpu is not None else "--"
        managed_str = "yes" if svc_config.managed else "coexist"

        table.add_row(
            DISPLAY_NAMES.get(svc_name, svc_name),
            str(st.port),
            svc_config.install_method,
            gpu_str,
            status_str,
            managed_str,
        )

    # Ollama instances
    if config.services.ollama.enabled:
        for inst in config.services.ollama.instances:
            from puente.detect import check_port

            running = check_port(inst.port)
            status_str = "[green]running[/green]" if running else "[red]stopped[/red]"
            gpu_str = str(inst.gpu) if inst.gpu is not None else "--"
            table.add_row(
                f"Ollama ({inst.name})",
                str(inst.port),
                "native",
                gpu_str,
                status_str,
                "yes" if config.services.ollama.managed else "coexist",
            )

    console.print(table)


# -- doctor --------------------------------------------------------------------


@app.command()
def doctor(
    services: bool = typer.Option(
        False, "--services", help="Also probe each enabled service's health endpoint"
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Machine-readable output for CI or monitoring"
    ),
):
    """Check the host environment, and optionally the running services.

    Read-only: reports problems and prints the command that would fix each one,
    but never installs or changes anything. Exits non-zero if any check fails,
    so it works as a deployment gate.
    """
    config = _require_config()
    checks = run_checks(config)

    # Service-level probes: only if enabled, and kept separate from host checks
    # because they report on runtime state rather than host readiness.
    if services:
        checks += _service_checks(config)

    if json_output:
        typer.echo(json.dumps(report_dict(checks), indent=2))
        raise typer.Exit(exit_code(checks))

    console.print("[bold]Host environment checks[/bold]\n")
    for c in checks:
        style = {
            "pass": "green",
            "warn": "yellow",
            "fail": "red",
            "skip": "dim",
        }[c.status]
        icon = {"pass": "PASS", "warn": "WARN", "fail": "FAIL", "skip": "SKIP"}[c.status]
        console.print(f"  [{style}]{icon}[/{style}] {c.name}")
        if c.detail:
            console.print(f"        [dim]{c.detail}[/dim]")
        if c.fix and c.status in ("warn", "fail"):
            console.print(f"        [dim]fix:[/dim] [cyan]{c.fix}[/cyan]")
        console.print()

    fails = [c for c in checks if c.status == "fail"]
    warns = [c for c in checks if c.status == "warn"]
    if fails:
        console.print(f"[red]{len(fails)} check(s) failed.[/red] See the fixes above.")
    elif warns:
        console.print(f"[yellow]All required checks passed, {len(warns)} warning(s).[/yellow]")
    else:
        console.print("[green]All checks passed.[/green]")

    raise typer.Exit(exit_code(checks))


def _service_checks(config: PuenteConfig) -> list[Check]:
    """TCP-probe each enabled service and report reachability."""
    checks = []
    for svc_name, svc_class in ALL_SERVICES.items():
        svc_config = getattr(config.services, svc_name, None)
        if svc_config is None or not svc_config.enabled:
            continue
        if svc_name == "ollama":
            continue
        svc = svc_class()
        healthy = svc.health_check(svc_config)
        name = DISPLAY_NAMES.get(svc_name, svc_name)
        checks.append(
            Check(
                f"service-{svc_name}",
                "pass" if healthy else "warn",
                "responding" if healthy else "not responding",
                None if healthy else f"Try `puente up {svc_name}`.",
            )
        )
        del name
    return checks


# -- gpu -----------------------------------------------------------------------


@app.command()
def gpu():
    """Detect and display available GPUs."""
    gpus = detect_gpus()
    print_gpu_table(gpus)


# -- connect -------------------------------------------------------------------


@app.command()
def connect():
    """Show connection details for external tools (editors, CLI clients)."""
    config = _require_config()

    import socket
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
    except socket.gaierror:
        local_ip = "127.0.0.1"

    console.print("\n[bold]Puente Stack — Connection Details[/bold]\n")

    # Ollama instances
    if config.services.ollama.enabled:
        for inst in config.services.ollama.instances:
            console.print(f"  [cyan]Ollama ({inst.name})[/cyan]")
            console.print(f"    Local:   http://127.0.0.1:{inst.port}")
            console.print(f"    Network: http://{local_ip}:{inst.port}")
            console.print()

    # Other services with APIs
    api_services = [
        ("open_webui", "Open WebUI"),
        ("speaches", "Speaches (TTS/STT)"),
        ("searxng", "SearXNG"),
    ]
    for svc_name, display in api_services:
        svc_config = getattr(config.services, svc_name, None)
        if svc_config and svc_config.enabled:
            port = svc_config.port
            console.print(f"  [cyan]{display}[/cyan]")
            console.print(f"    http://{local_ip}:{port}")
            console.print()

    # Editor connection guides
    primary_port = 11434
    if config.services.ollama.enabled and config.services.ollama.instances:
        primary_port = config.services.ollama.instances[0].port

    base_url = f"http://{local_ip}:{primary_port}"

    console.print("[bold]Connect your editor:[/bold]\n")
    console.print(f"  [green]Continue[/green] (VS Code / JetBrains)")
    console.print(f"    Set API base to: {base_url}")
    console.print()
    console.print(f"  [green]OpenCode[/green]")
    console.print(f"    OPENAI_API_BASE={base_url}/v1 opencode")
    console.print()
    console.print(f"  [green]Claude Code[/green]")
    console.print(f"    Use --api-base {base_url}/v1")
    console.print()
    console.print(f"  [green]Claude Desktop[/green]")
    console.print(f"    Configure MCP to connect to {base_url}")
    console.print()
    console.print(f"  [green]Any OpenAI-compatible client[/green]")
    console.print(f"    OPENAI_API_BASE={base_url}/v1")
    console.print(f"    OPENAI_API_KEY=not-needed")
    console.print()


# -- portal --------------------------------------------------------------------


@app.command()
def portal(
    host: str = typer.Option("localhost", help="Hostname or IP for service URLs"),
    serve: bool = typer.Option(False, help="Enable the portal nginx container in the stack"),
    port: int = typer.Option(8080, help="Port for the portal (when using --serve)"),
):
    """Generate a service launcher page from your config."""
    from puente.portal import write_portal

    config = _require_config()

    # Auto-detect host IP if "localhost"
    if host == "localhost":
        import socket
        try:
            hostname = socket.gethostname()
            detected = socket.gethostbyname(hostname)
            if detected != "127.0.0.1":
                host = detected
        except socket.gaierror:
            pass

    portal_dir = write_portal(config, host)
    console.print(f"[green]Portal generated:[/green] {portal_dir}/index.html")
    console.print(f"  Views: PoC (default) | Student | Backend")

    if serve:
        # Persist portal config so compose generation picks it up on every
        # `puente up`, instead of hand-patching docker-compose.yml (which gets
        # regenerated each run).
        config.services.portal.enabled = True
        config.services.portal.port = port
        config.services.portal.host = host
        save_config(config)
        write_compose(config)
        console.print(
            f"[green]Portal enabled in puente.yml (port {port})[/green]"
        )
        console.print(f"  Run [bold cyan]puente up[/bold cyan] to start it.")
    else:
        portal_path = portal_dir / "index.html"
        console.print(f"\n  Open the file directly: file://{portal_path}")
        console.print(f"  Or use [bold]--serve[/bold] to add an nginx container to your stack.")

    console.print()


@app.command()
def capabilities(
    backend: str | None = typer.Option(
        None, help="Assess against a backend: ollama (default) or llama.cpp"
    ),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable output"),
):
    """What this host can actually do, and what it cannot.

    Detects hardware and reports a blunt verdict per capability — usable, or not,
    with the reason. Read-only; nothing is installed or started. This is the
    question "can I run this?" answered before you find out by watching a
    container fail.
    """
    from puente.capabilities import detect_host, report_for

    report = report_for(detect_host(), backend)

    if json_output:
        typer.echo(json.dumps(report.to_dict(), indent=2))
        return

    console.print(report.render())


# -- version -------------------------------------------------------------------


@app.command()
def version():
    """Show version."""
    console.print(f"puente {__version__}")


# -- helpers -------------------------------------------------------------------


def _ufw_warning_if_needed() -> None:
    """On Linux, warn if UFW is active without a rule for the puente bridge.

    Puente's containers live on a custom bridge named `puente0`. UFW's default
    policy drops inbound traffic on unknown interfaces, which silently breaks
    container-to-host connections (e.g. Open WebUI → native Ollama on the host).
    One rule fixes it: `sudo ufw allow in on puente0`.
    """
    try:
        result = subprocess.run(
            ["ufw", "status"], capture_output=True, text=True, timeout=2
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return
    if result.returncode != 0:
        return
    output = result.stdout
    if "Status: active" not in output:
        return
    if "puente0" in output:
        return
    console.print(
        "[yellow]UFW is active but has no rule for the puente0 bridge.[/yellow]\n"
        "[yellow]Containers may be unable to reach host services (e.g. native Ollama).[/yellow]\n"
        "[yellow]Fix with:[/yellow] [bold]sudo ufw allow in on puente0[/bold]"
    )


def _warn_invalid_gpu_pins(config: PuenteConfig, scoped: str | None = None) -> None:
    """Print any `gpu:` pin that doesn't match real hardware.

    Advisory, not fatal: `puente up` is often the first command run on a box
    whose driver is mid-repair, and refusing to start the whole stack over one
    bad pin would be worse than reporting it. The compose file still goes
    through, so Docker remains the final authority — this just turns an opaque
    failure into a named one.
    """
    from puente.doctor import check_gpu_pins

    try:
        checks = check_gpu_pins(config)
    except Exception:  # detection is best-effort; never block startup on it
        return

    for c in checks:
        if c.status == "fail":
            console.print(f"[red]GPU pin problem:[/red] {c.detail}")
            if c.fix:
                console.print(f"  [dim]{c.fix}[/dim]")
        elif c.status == "warn":
            console.print(f"[yellow]{c.name}:[/yellow] {c.detail}")


def _require_config() -> PuenteConfig:
    """Load the stack config or exit with a helpful message.

    Never falls back to schema defaults here. Every caller is about to generate
    or overwrite deployment artifacts from whatever config it returns, so a
    missing file has to stop the command rather than quietly write the
    3-service default over a real stack.

    `--config` wins; otherwise discovery already ran in the CLI callback, and
    failing here means it found nothing. An explicit path that exists always
    loads, even if discovery would have found a different file.
    """
    explicit = _resolved_config_path()
    if explicit is not None:
        return load_config(explicit)
    try:
        return load_config(require=True)
    except ConfigNotFound as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(1) from exc


def _resolved_config_path() -> Path | None:
    """The config the CLI callback settled on, or None if nothing was found.

    Set once in the `main` callback: from `--config` if given, otherwise by
    searching upward from the cwd. None means discovery failed, which is the
    case `load_config(require=True)` turns into a helpful error.
    """
    return _active_config


def _print_config_summary(config: PuenteConfig) -> None:
    """Print a quick summary of enabled services."""
    for svc_name in ALL_SERVICES:
        svc_config = getattr(config.services, svc_name, None)
        if svc_config and svc_config.enabled:
            name = DISPLAY_NAMES.get(svc_name, svc_name)
            port = svc_config.port or ""
            gpu_str = f" (GPU {svc_config.gpu})" if svc_config.gpu is not None else ""
            managed = "" if svc_config.managed else " [dim](coexist)[/dim]"
            console.print(f"  [green]+[/green] {name} :{port}{gpu_str}{managed}")
        else:
            name = DISPLAY_NAMES.get(svc_name, svc_name)
            console.print(f"  [dim]-[/dim] [dim]{name}[/dim]")

    if config.services.ollama.enabled:
        for inst in config.services.ollama.instances:
            gpu_str = f" (GPU {inst.gpu})" if inst.gpu is not None else ""
            console.print(f"  [green]+[/green] Ollama {inst.name} :{inst.port}{gpu_str}")
