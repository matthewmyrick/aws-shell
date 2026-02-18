"""STS commands."""
from rich.console import Console
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("sts", handle_sts, "Security Token Service commands")


def handle_sts(args, config, session_manager):
    subcommands = {
        "get-caller-identity": get_caller_identity,
    }
    subcommand_dispatch("sts", subcommands, args, config, session_manager)


def get_caller_identity(args, config, session_manager):
    identity = session_manager.get_caller_identity()
    console.print(f"  [bold]Account:[/bold]  {identity['Account']}")
    console.print(f"  [bold]UserID:[/bold]   {identity['UserId']}")
    console.print(f"  [bold]ARN:[/bold]      {identity['Arn']}")
