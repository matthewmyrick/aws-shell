"""CloudWatch commands."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("cw", handle_cw, "CloudWatch monitoring commands")


def handle_cw(args, config, session_manager):
    subcommands = {
        "list-alarms": list_alarms,
        "describe-alarm": describe_alarm,
        "list-log-groups": list_log_groups,
        "list-metrics": list_metrics,
        "get-config": get_config,
    }
    subcommand_dispatch("cw", subcommands, args, config, session_manager)


def list_alarms(args, config, session_manager):
    client = session_manager.client("cloudwatch")
    paginator = client.get_paginator("describe_alarms")

    table = Table(title=f"CloudWatch Alarms ({config.region})")
    table.add_column("Alarm Name", style="cyan")
    table.add_column("State", style="bold")
    table.add_column("Metric", style="green")
    table.add_column("Namespace", style="yellow")
    table.add_column("Comparison")

    count = 0
    for page in paginator.paginate():
        for alarm in page.get("MetricAlarms", []):
            state = alarm.get("StateValue", "")
            state_display = {
                "OK": "[green]OK[/green]",
                "ALARM": "[red]ALARM[/red]",
                "INSUFFICIENT_DATA": "[yellow]INSUFFICIENT_DATA[/yellow]",
            }.get(state, state)

            table.add_row(
                alarm["AlarmName"],
                state_display,
                alarm.get("MetricName", ""),
                alarm.get("Namespace", ""),
                f"{alarm.get('ComparisonOperator', '')} {alarm.get('Threshold', '')}",
            )
            count += 1

    console.print(table)
    console.print(f"[dim]{count} alarm(s) found[/dim]")


def describe_alarm(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] cw describe-alarm <alarm-name>")
        return
    client = session_manager.client("cloudwatch")
    response = client.describe_alarms(AlarmNames=[args[0]])
    print_json(response.get("MetricAlarms", []))


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] cw get-config <alarm-name>")
        return
    client = session_manager.client("cloudwatch")
    response = client.describe_alarms(AlarmNames=[args[0]])
    print_json(response.get("MetricAlarms", []))


def list_log_groups(args, config, session_manager):
    client = session_manager.client("logs")
    paginator = client.get_paginator("describe_log_groups")

    table = Table(title=f"CloudWatch Log Groups ({config.region})")
    table.add_column("Log Group Name", style="cyan")
    table.add_column("Stored Bytes", style="yellow")
    table.add_column("Retention (days)")
    table.add_column("Created")

    count = 0
    for page in paginator.paginate():
        for group in page.get("logGroups", []):
            stored = group.get("storedBytes", 0)
            if stored > 1_073_741_824:
                stored_str = f"{stored / 1_073_741_824:.1f} GB"
            elif stored > 1_048_576:
                stored_str = f"{stored / 1_048_576:.1f} MB"
            elif stored > 1024:
                stored_str = f"{stored / 1024:.1f} KB"
            else:
                stored_str = f"{stored} B"

            table.add_row(
                group["logGroupName"],
                stored_str,
                str(group.get("retentionInDays", "Never expire")),
                str(group.get("creationTime", "")),
            )
            count += 1

    console.print(table)
    console.print(f"[dim]{count} log group(s) found[/dim]")


def list_metrics(args, config, session_manager):
    client = session_manager.client("cloudwatch")

    kwargs = {}
    if args:
        kwargs["Namespace"] = args[0]

    response = client.list_metrics(**kwargs)

    table = Table(title=f"CloudWatch Metrics ({config.region})")
    table.add_column("Namespace", style="cyan")
    table.add_column("Metric Name", style="green")
    table.add_column("Dimensions", style="yellow")

    for metric in response.get("Metrics", [])[:100]:
        dims = ", ".join(
            f"{d['Name']}={d['Value']}" for d in metric.get("Dimensions", [])
        )
        table.add_row(
            metric.get("Namespace", ""),
            metric.get("MetricName", ""),
            dims,
        )

    total = len(response.get("Metrics", []))
    shown = min(total, 100)
    console.print(table)
    console.print(f"[dim]{shown} of {total} metric(s) shown[/dim]")
