"""Global Accelerator commands."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("ga", handle_ga, "Global Accelerator commands")


def handle_ga(args, config, session_manager):
    subcommands = {
        "list-accelerators": list_accelerators,
        "describe-accelerator": describe_accelerator,
        "get-config": get_config,
    }
    subcommand_dispatch("ga", subcommands, args, config, session_manager)


def list_accelerators(args, config, session_manager):
    client = session_manager.client("globalaccelerator")
    response = client.list_accelerators()

    table = Table(title="Global Accelerators")
    table.add_column("Name", style="cyan")
    table.add_column("ARN", style="dim")
    table.add_column("Status", style="bold")
    table.add_column("Enabled", style="yellow")
    table.add_column("DNS Name", style="green")

    for accel in response.get("Accelerators", []):
        status = accel.get("Status", "")
        status_display = {
            "DEPLOYED": "[green]DEPLOYED[/green]",
            "IN_PROGRESS": "[yellow]IN_PROGRESS[/yellow]",
        }.get(status, status)

        table.add_row(
            accel.get("Name", ""),
            accel.get("AcceleratorArn", ""),
            status_display,
            str(accel.get("Enabled", False)),
            accel.get("DnsName", ""),
        )
    console.print(table)


def describe_accelerator(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] ga describe-accelerator <accelerator-arn>")
        return
    client = session_manager.client("globalaccelerator")
    response = client.describe_accelerator(AcceleratorArn=args[0])
    print_json(response.get("Accelerator", {}))


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] ga get-config <accelerator-arn>")
        return
    client = session_manager.client("globalaccelerator")
    response = client.describe_accelerator(AcceleratorArn=args[0])
    print_json(response.get("Accelerator", {}))
