"""SSM (Systems Manager) commands."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("ssm", handle_ssm, "Systems Manager commands")


def handle_ssm(args, config, session_manager):
    subcommands = {
        "list-parameters": list_parameters,
        "get-parameter": get_parameter,
        "list-instances": list_instances,
        "get-config": get_config,
    }
    subcommand_dispatch("ssm", subcommands, args, config, session_manager)


def list_parameters(args, config, session_manager):
    client = session_manager.client("ssm")
    paginator = client.get_paginator("describe_parameters")

    table = Table(title=f"SSM Parameters ({config.region})")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Tier", style="yellow")
    table.add_column("Last Modified")
    table.add_column("Version")

    count = 0
    for page in paginator.paginate():
        for param in page.get("Parameters", []):
            table.add_row(
                param.get("Name", ""),
                param.get("Type", ""),
                param.get("Tier", ""),
                str(param.get("LastModifiedDate", "")),
                str(param.get("Version", "")),
            )
            count += 1

    console.print(table)
    console.print(f"[dim]{count} parameter(s) found[/dim]")


def get_parameter(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] ssm get-parameter <parameter-name>")
        return
    client = session_manager.client("ssm")
    response = client.get_parameter(Name=args[0], WithDecryption=True)
    print_json(response.get("Parameter", {}))


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] ssm get-config <parameter-name>")
        return
    client = session_manager.client("ssm")
    response = client.get_parameter(Name=args[0], WithDecryption=True)
    print_json(response.get("Parameter", {}))


def list_instances(args, config, session_manager):
    client = session_manager.client("ssm")
    response = client.describe_instance_information()

    table = Table(title=f"SSM Managed Instances ({config.region})")
    table.add_column("Instance ID", style="cyan")
    table.add_column("Ping Status", style="bold")
    table.add_column("Platform", style="green")
    table.add_column("Platform Version")
    table.add_column("Agent Version", style="yellow")

    for instance in response.get("InstanceInformationList", []):
        ping = instance.get("PingStatus", "")
        ping_display = {
            "Online": "[green]Online[/green]",
            "ConnectionLost": "[red]ConnectionLost[/red]",
            "Inactive": "[yellow]Inactive[/yellow]",
        }.get(ping, ping)

        table.add_row(
            instance.get("InstanceId", ""),
            ping_display,
            instance.get("PlatformType", ""),
            instance.get("PlatformVersion", ""),
            instance.get("AgentVersion", ""),
        )
    console.print(table)
