"""EC2 commands."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("ec2", handle_ec2, "EC2 instance management commands")


def handle_ec2(args, config, session_manager):
    subcommands = {
        "list-instances": list_instances,
        "describe-instance": describe_instance,
        "start-instance": start_instance,
        "stop-instance": stop_instance,
        "get-config": get_config,
    }
    subcommand_dispatch("ec2", subcommands, args, config, session_manager)


def list_instances(args, config, session_manager):
    ec2 = session_manager.client("ec2")
    paginator = ec2.get_paginator("describe_instances")

    table = Table(title=f"EC2 Instances ({config.region})")
    table.add_column("Instance ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("State", style="bold")
    table.add_column("Type", style="yellow")
    table.add_column("Private IP")
    table.add_column("Public IP")
    table.add_column("Launch Time")

    count = 0
    for page in paginator.paginate():
        for reservation in page["Reservations"]:
            for instance in reservation["Instances"]:
                name = ""
                for tag in instance.get("Tags", []):
                    if tag["Key"] == "Name":
                        name = tag["Value"]
                state = instance["State"]["Name"]
                state_display = {
                    "running": "[green]running[/green]",
                    "stopped": "[red]stopped[/red]",
                    "pending": "[yellow]pending[/yellow]",
                    "terminated": "[dim]terminated[/dim]",
                    "shutting-down": "[yellow]shutting-down[/yellow]",
                    "stopping": "[yellow]stopping[/yellow]",
                }.get(state, state)

                table.add_row(
                    instance["InstanceId"],
                    name,
                    state_display,
                    instance.get("InstanceType", ""),
                    instance.get("PrivateIpAddress", ""),
                    instance.get("PublicIpAddress", ""),
                    str(instance.get("LaunchTime", "")),
                )
                count += 1

    console.print(table)
    console.print(f"[dim]{count} instance(s) found[/dim]")


def describe_instance(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] ec2 describe-instance <instance-id>")
        return
    ec2 = session_manager.client("ec2")
    response = ec2.describe_instances(InstanceIds=[args[0]])
    print_json(response["Reservations"])


def start_instance(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] ec2 start-instance <instance-id>")
        return
    confirm = console.input(
        f"[bold yellow]Start instance {args[0]}? (yes/no):[/bold yellow] "
    )
    if confirm.lower() == "yes":
        ec2 = session_manager.client("ec2")
        ec2.start_instances(InstanceIds=[args[0]])
        console.print(f"[green]Instance {args[0]} starting...[/green]")
    else:
        console.print("[dim]Cancelled.[/dim]")


def stop_instance(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] ec2 stop-instance <instance-id>")
        return
    confirm = console.input(
        f"[bold yellow]Stop instance {args[0]}? (yes/no):[/bold yellow] "
    )
    if confirm.lower() == "yes":
        ec2 = session_manager.client("ec2")
        ec2.stop_instances(InstanceIds=[args[0]])
        console.print(f"[green]Instance {args[0]} stopping...[/green]")
    else:
        console.print("[dim]Cancelled.[/dim]")


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] ec2 get-config <instance-id>")
        return
    ec2 = session_manager.client("ec2")
    response = ec2.describe_instances(InstanceIds=[args[0]])
    print_json(response["Reservations"])


