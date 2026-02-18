"""CloudFormation commands."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()

STACK_STATUS_STYLES = {
    "CREATE_COMPLETE": "[green]CREATE_COMPLETE[/green]",
    "UPDATE_COMPLETE": "[green]UPDATE_COMPLETE[/green]",
    "DELETE_COMPLETE": "[dim]DELETE_COMPLETE[/dim]",
    "CREATE_IN_PROGRESS": "[yellow]CREATE_IN_PROGRESS[/yellow]",
    "UPDATE_IN_PROGRESS": "[yellow]UPDATE_IN_PROGRESS[/yellow]",
    "DELETE_IN_PROGRESS": "[yellow]DELETE_IN_PROGRESS[/yellow]",
    "ROLLBACK_COMPLETE": "[red]ROLLBACK_COMPLETE[/red]",
    "ROLLBACK_IN_PROGRESS": "[red]ROLLBACK_IN_PROGRESS[/red]",
    "CREATE_FAILED": "[bold red]CREATE_FAILED[/bold red]",
    "UPDATE_FAILED": "[bold red]UPDATE_FAILED[/bold red]",
    "DELETE_FAILED": "[bold red]DELETE_FAILED[/bold red]",
}


def register(registry):
    registry.register("cfn", handle_cfn, "CloudFormation stack management")


def handle_cfn(args, config, session_manager):
    subcommands = {
        "list-stacks": list_stacks,
        "describe-stack": describe_stack,
        "get-config": get_config,
    }
    subcommand_dispatch("cfn", subcommands, args, config, session_manager)


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] cfn get-config <stack-name>")
        return
    cfn = session_manager.client("cloudformation")
    response = cfn.describe_stacks(StackName=args[0])
    print_json(response["Stacks"])


def list_stacks(args, config, session_manager):
    cfn = session_manager.client("cloudformation")
    paginator = cfn.get_paginator("list_stacks")

    table = Table(title=f"CloudFormation Stacks ({config.region})")
    table.add_column("Stack Name", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Created", style="green")
    table.add_column("Updated")
    table.add_column("Description", max_width=40)

    # Filter out deleted stacks by default
    active_statuses = [
        "CREATE_IN_PROGRESS", "CREATE_COMPLETE", "CREATE_FAILED",
        "ROLLBACK_IN_PROGRESS", "ROLLBACK_COMPLETE", "ROLLBACK_FAILED",
        "UPDATE_IN_PROGRESS", "UPDATE_COMPLETE", "UPDATE_FAILED",
        "UPDATE_ROLLBACK_IN_PROGRESS", "UPDATE_ROLLBACK_COMPLETE",
        "UPDATE_ROLLBACK_FAILED", "REVIEW_IN_PROGRESS",
        "IMPORT_IN_PROGRESS", "IMPORT_COMPLETE", "IMPORT_ROLLBACK_IN_PROGRESS",
        "IMPORT_ROLLBACK_COMPLETE", "IMPORT_ROLLBACK_FAILED",
    ]

    count = 0
    for page in paginator.paginate(StackStatusFilter=active_statuses):
        for stack in page.get("StackSummaries", []):
            status = stack["StackStatus"]
            status_display = STACK_STATUS_STYLES.get(status, status)
            table.add_row(
                stack["StackName"],
                status_display,
                str(stack.get("CreationTime", "")),
                str(stack.get("LastUpdatedTime", "")),
                (stack.get("TemplateDescription") or "")[:40],
            )
            count += 1

    console.print(table)
    console.print(f"[dim]{count} stack(s) found[/dim]")


def describe_stack(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] cfn describe-stack <stack-name>")
        return

    cfn = session_manager.client("cloudformation")
    response = cfn.describe_stacks(StackName=args[0])

    if response["Stacks"]:
        stack = response["Stacks"][0]

        console.print(f"\n[bold cyan]{stack['StackName']}[/bold cyan]")
        status = stack["StackStatus"]
        status_display = STACK_STATUS_STYLES.get(status, status)
        console.print(f"  [bold]Status:[/bold]      {status_display}")
        console.print(f"  [bold]Created:[/bold]     {stack.get('CreationTime', '')}")
        console.print(f"  [bold]Updated:[/bold]     {stack.get('LastUpdatedTime', 'N/A')}")
        console.print(f"  [bold]Description:[/bold] {stack.get('Description', 'N/A')}")

        # Show outputs
        outputs = stack.get("Outputs", [])
        if outputs:
            console.print("\n  [bold]Outputs:[/bold]")
            out_table = Table()
            out_table.add_column("Key", style="cyan")
            out_table.add_column("Value", style="green")
            out_table.add_column("Description")
            for out in outputs:
                out_table.add_row(
                    out["OutputKey"],
                    out["OutputValue"],
                    out.get("Description", ""),
                )
            console.print(out_table)

        # Show parameters
        params = stack.get("Parameters", [])
        if params:
            console.print("\n  [bold]Parameters:[/bold]")
            param_table = Table()
            param_table.add_column("Key", style="cyan")
            param_table.add_column("Value", style="green")
            for p in params:
                param_table.add_row(p["ParameterKey"], p["ParameterValue"])
            console.print(param_table)

        console.print()
