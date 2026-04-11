"""Puente CLI — local AI stack orchestrator."""

from __future__ import annotations

import subprocess
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from puente import __version__
from puente.compose import generate_compose, write_compose
from puente.detect import detect_all
from puente.gpu import detect_gpus, print_gpu_table, suggest_gpu_assignment
from puente.models import (
    CONFIG_FILE,
    OllamaConfig,
    OllamaInstance,
    PuenteConfig,
    ServiceConfig,
    StackConfig,
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


# -- Service display names for pretty printing --------------------------------

DISPLAY_NAMES = {
    "ollama": "Ollama",
    "open_webui": "Open WebUI",
    "speaches": "Speaches",
    "comfyui": "ComfyUI",
    "searxng": "SearXNG",
    "vane": "Vane (AI Search)",
    "anythingllm": "AnythingLLM",
    "open_notebook": "Open Notebook AI",
    "stirling_pdf": "Stirling PDF",
    "excalidraw": "Excalidraw",
    "open_terminal": "Open Terminal",
    "citesight": "CiteSight",
    "jupyter": "JupyterLab",
    "deeptutor": "DeepTutor",
    "musicgen": "MusicGen",
    "swarmui": "SwarmUI",
    "fooocus": "Fooocus",
}


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

    # Always regenerate so upstream changes to compose.py / service fragments
    # are picked up without requiring users to manually delete the file.
    write_compose(config, compose_path)

    # Keep the portal launcher page in sync with current config.
    if config.services.portal.enabled:
        from puente.portal import write_portal

        write_portal(config, config.services.portal.host)

    _ufw_warning_if_needed()

    # Start Docker services
    if compose_path.exists() and compose_path.stat().st_size > 20:
        cmd = ["docker", "compose", "-f", str(compose_path), "up", "-d"]
        # Ollama is the only non-Docker service; everything else (including
        # ComfyUI) is a regular compose service and can be scoped normally.
        if service and service != "ollama":
            compose_name = service.replace("_", "-")
            cmd.append(compose_name)
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
            compose_name = service.replace("_", "-")
            cmd.extend(["--remove-orphans", compose_name])
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
    service: str = typer.Argument(..., help="Service name (e.g. musicgen, swarmui)"),
    port: int | None = typer.Option(None, help="Override the service port"),
    gpu: int | None = typer.Option(None, help="GPU id to assign (for GPU services)"),
    review: bool = typer.Option(
        False,
        "--review",
        help="Mark the service as Under Evaluation in the portal",
    ),
):
    """Enable a service in puente.yml without touching other config."""
    name = _resolve_service(service)
    config = _require_config()
    svc_config = getattr(config.services, name)
    svc_config.enabled = True
    if port is not None:
        svc_config.port = port
    if gpu is not None:
        svc_config.gpu = gpu
    if review:
        svc_config.review = True
    save_config(config)
    write_compose(config)
    console.print(f"[green]Enabled[/green] {DISPLAY_NAMES.get(name, name)} in puente.yml")
    console.print(f"  Run [bold cyan]puente up {name}[/bold cyan] to start it.")


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
def doctor():
    """Health check all enabled services."""
    config = _require_config()
    all_ok = True

    console.print("[bold]Running health checks...[/bold]\n")

    for svc_name, svc_class in ALL_SERVICES.items():
        svc_config = getattr(config.services, svc_name, None)
        if svc_config is None or not svc_config.enabled:
            continue

        svc = svc_class()
        healthy = svc.health_check(svc_config)
        name = DISPLAY_NAMES.get(svc_name, svc_name)
        if healthy:
            console.print(f"  [green]PASS[/green] {name}")
        else:
            console.print(f"  [red]FAIL[/red] {name}")
            all_ok = False

    if all_ok:
        console.print("\n[green]All services healthy.[/green]")
    else:
        console.print("\n[yellow]Some services are not responding.[/yellow]")


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


def _require_config() -> PuenteConfig:
    """Load config or exit with a helpful message."""
    if not Path(CONFIG_FILE).exists():
        console.print(f"[red]No {CONFIG_FILE} found.[/red] Run [bold]puente init[/bold] first.")
        raise typer.Exit(1)
    return load_config()


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
