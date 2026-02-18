"""DynamoDB commands."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("dynamodb", handle_dynamodb, "DynamoDB table commands")


def handle_dynamodb(args, config, session_manager):
    subcommands = {
        "list-tables": list_tables,
        "describe-table": describe_table,
        "scan": scan_table,
        "get-config": get_config,
    }
    subcommand_dispatch("dynamodb", subcommands, args, config, session_manager)


def list_tables(args, config, session_manager):
    client = session_manager.client("dynamodb")
    response = client.list_tables()

    table = Table(title=f"DynamoDB Tables ({config.region})")
    table.add_column("Table Name", style="cyan")

    for name in response.get("TableNames", []):
        table.add_row(name)

    count = len(response.get("TableNames", []))
    console.print(table)
    console.print(f"[dim]{count} table(s) found[/dim]")


def describe_table(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] dynamodb describe-table <table-name>")
        return
    client = session_manager.client("dynamodb")
    response = client.describe_table(TableName=args[0])
    print_json(response.get("Table", {}))


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] dynamodb get-config <table-name>")
        return
    client = session_manager.client("dynamodb")
    response = client.describe_table(TableName=args[0])
    print_json(response.get("Table", {}))


def scan_table(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] dynamodb scan <table-name> [limit]")
        return
    client = session_manager.client("dynamodb")
    limit = 10
    if len(args) > 1:
        try:
            limit = int(args[1])
        except ValueError:
            console.print("[red]Limit must be a number[/red]")
            return

    response = client.scan(TableName=args[0], Limit=limit)
    items = response.get("Items", [])
    print_json(items)
    console.print(f"[dim]{len(items)} item(s) returned (limit: {limit})[/dim]")
