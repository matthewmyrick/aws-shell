"""Subcommand dispatch helper."""
from rich.console import Console

console = Console()


def subcommand_dispatch(service_name, subcommands, args, config, session_manager):
    if not args:
        console.print(
            f"[bold yellow]Usage:[/bold yellow] {service_name} <subcommand>\n"
            f"Available subcommands: {', '.join(subcommands.keys())}\n"
            f"Type [bold cyan]help {service_name}[/bold cyan] for details."
        )
        return
    sub = args[0].lower()
    remaining = args[1:]
    if sub in subcommands:
        subcommands[sub](remaining, config, session_manager)
    else:
        console.print(
            f"[bold red]Unknown subcommand:[/bold red] {service_name} {sub}\n"
            f"Available: {', '.join(subcommands.keys())}"
        )
