"""Welcome screen and first-boot documentation."""
from rich.console import Console
from rich.panel import Panel

console = Console()

BANNER = r"""
    ___        ______    ____  _          _ _
   / \ \      / / ___|  / ___|| |__   ___| | |
  / _ \ \ /\ / /\___ \  \___ \| '_ \ / _ \ | |
 / ___ \ V  V /  ___) |  ___) | | | |  __/ | |
/_/   \_\_/\_/  |____/  |____/|_| |_|\___|_|_|
"""


def show_welcome(config, session_manager):
    console.print(BANNER, style="bold #ff9900")
    console.print(
        Panel(
            "[bold]Welcome to AWS Shell![/bold]\n\n"
            "An interactive shell for exploring your AWS environment.\n"
            "Type [bold cyan]help[/bold cyan] for available commands, "
            "or [bold cyan]help <service>[/bold cyan] for service-specific help.\n"
            "Type [bold cyan]py[/bold cyan] to enter Python REPL with boto3 pre-loaded.\n"
            "Press [bold]Tab[/bold] for auto-completion. "
            "Press [bold]Ctrl+D[/bold] to exit.",
            title="AWS Interactive Shell v0.1.0",
            border_style="#ff9900",
        )
    )

    try:
        identity = session_manager.get_caller_identity()
        console.print(
            f"  Authenticated as: [bold green]{identity['Arn']}[/bold green]"
        )
        console.print(
            f"  Account: [bold]{identity['Account']}[/bold]  |  "
            f"Region: [bold]{config.region}[/bold]  |  "
            f"Profile: [bold]{config.profile}[/bold]\n"
        )
    except Exception as e:
        console.print(
            f"  [bold red]Warning:[/bold red] Could not validate AWS credentials: {e}"
        )
        console.print(
            "  Some commands may not work. "
            "Use [bold]use-profile <name>[/bold] to switch profiles.\n"
        )
