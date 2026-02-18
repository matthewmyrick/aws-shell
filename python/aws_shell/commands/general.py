"""General shell commands."""
import os

from rich.console import Console
from rich.table import Table

console = Console()


def register(registry):
    registry.register("use-profile", cmd_use_profile, "Switch AWS profile")
    registry.register("set-region", cmd_set_region, "Switch AWS region")
    registry.register("set-output", cmd_set_output, "Set output format (table|json|text)")
    registry.register("whoami", cmd_whoami, "Show current AWS identity")
    registry.register("services", cmd_services, "List available AWS services")
    registry.register("clear", cmd_clear, "Clear the terminal")
    registry.register("exit", cmd_exit, "Exit the shell")
    registry.register("quit", cmd_exit, "Exit the shell")


def cmd_use_profile(args, config, session_manager):
    if not args:
        console.print(f"[yellow]Current profile:[/yellow] {config.profile}")
        console.print("[yellow]Usage:[/yellow] use-profile <profile-name>")
        return
    profile = args[0]
    session_manager.switch_profile(profile)
    console.print(f"[green]Switched to profile:[/green] {profile}")
    try:
        identity = session_manager.get_caller_identity()
        console.print(f"  Authenticated as: [bold]{identity['Arn']}[/bold]")
    except Exception as e:
        console.print(f"  [bold red]Warning:[/bold red] Could not validate credentials: {e}")


def cmd_set_region(args, config, session_manager):
    if not args:
        console.print(f"[yellow]Current region:[/yellow] {config.region}")
        console.print("[yellow]Usage:[/yellow] set-region <region>")
        return
    region = args[0]
    session_manager.switch_region(region)
    console.print(f"[green]Region set to:[/green] {region}")


def cmd_set_output(args, config, session_manager):
    if not args:
        console.print(f"[yellow]Current output format:[/yellow] {config.output_format}")
        console.print("[yellow]Usage:[/yellow] set-output <table|json|text>")
        return
    fmt = args[0].lower()
    if config.set_output(fmt):
        console.print(f"[green]Output format set to:[/green] {fmt}")
    else:
        console.print("[red]Invalid format.[/red] Choose: table, json, text")


def cmd_whoami(args, config, session_manager):
    try:
        identity = session_manager.get_caller_identity()
        console.print(f"  [bold]Account:[/bold]  {identity['Account']}")
        console.print(f"  [bold]UserID:[/bold]   {identity['UserId']}")
        console.print(f"  [bold]ARN:[/bold]      {identity['Arn']}")
        console.print(f"  [bold]Profile:[/bold]  {config.profile}")
        console.print(f"  [bold]Region:[/bold]   {config.region}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


def cmd_services(args, config, session_manager):
    services = session_manager.get_available_services()
    table = Table(title="Available AWS Services")
    table.add_column("#", style="dim")
    table.add_column("Service", style="cyan")
    for i, svc in enumerate(sorted(services), 1):
        table.add_row(str(i), svc)
    console.print(table)
    console.print(f"\n[dim]{len(services)} services available[/dim]")


def cmd_clear(args, config, session_manager):
    os.system("clear" if os.name != "nt" else "cls")


def cmd_exit(args, config, session_manager):
    console.print("[dim]Goodbye![/dim]")
    raise EOFError
