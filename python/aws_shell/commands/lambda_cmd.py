"""Lambda commands."""
import json

from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("lambda", handle_lambda, "Lambda function management")


def handle_lambda(args, config, session_manager):
    subcommands = {
        "list-functions": list_functions,
        "describe-function": describe_function,
        "invoke": invoke_function,
        "get-config": get_config,
    }
    subcommand_dispatch("lambda", subcommands, args, config, session_manager)


def list_functions(args, config, session_manager):
    lam = session_manager.client("lambda")
    paginator = lam.get_paginator("list_functions")

    table = Table(title=f"Lambda Functions ({config.region})")
    table.add_column("Function Name", style="cyan")
    table.add_column("Runtime", style="green")
    table.add_column("Memory (MB)", style="yellow", justify="right")
    table.add_column("Timeout (s)", justify="right")
    table.add_column("Last Modified")
    table.add_column("Description", max_width=40)

    count = 0
    for page in paginator.paginate():
        for fn in page["Functions"]:
            table.add_row(
                fn["FunctionName"],
                fn.get("Runtime", "N/A"),
                str(fn.get("MemorySize", "")),
                str(fn.get("Timeout", "")),
                fn.get("LastModified", ""),
                fn.get("Description", "")[:40],
            )
            count += 1

    console.print(table)
    console.print(f"[dim]{count} function(s) found[/dim]")


def describe_function(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] lambda describe-function <function-name>")
        return
    lam = session_manager.client("lambda")
    response = lam.get_function(FunctionName=args[0])
    print_json(response)


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] lambda get-config <function-name>")
        return
    lam = session_manager.client("lambda")
    response = lam.get_function(FunctionName=args[0])
    print_json(response)


def invoke_function(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] lambda invoke <function-name> [payload-json]")
        return

    func_name = args[0]
    payload = args[1] if len(args) > 1 else "{}"

    lam = session_manager.client("lambda")
    console.print(f"[yellow]Invoking {func_name}...[/yellow]")

    response = lam.invoke(
        FunctionName=func_name,
        Payload=payload.encode("utf-8"),
    )

    status = response["StatusCode"]
    result = response["Payload"].read().decode("utf-8")

    console.print(f"[bold]Status:[/bold] {status}")
    if response.get("FunctionError"):
        console.print(f"[bold red]Error:[/bold red] {response['FunctionError']}")

    try:
        parsed = json.loads(result)
        print_json(parsed)
    except json.JSONDecodeError:
        console.print(result)
