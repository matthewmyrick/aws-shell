"""SQS (Simple Queue Service) commands."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("sqs", handle_sqs, "SQS queue commands")


def handle_sqs(args, config, session_manager):
    subcommands = {
        "list-queues": list_queues,
        "describe-queue": describe_queue,
        "get-queue-attributes": get_queue_attributes,
        "get-config": get_config,
    }
    subcommand_dispatch("sqs", subcommands, args, config, session_manager)


def list_queues(args, config, session_manager):
    client = session_manager.client("sqs")
    response = client.list_queues()

    table = Table(title=f"SQS Queues ({config.region})")
    table.add_column("Queue URL", style="cyan")

    for url in response.get("QueueUrls", []):
        table.add_row(url)

    count = len(response.get("QueueUrls", []))
    console.print(table)
    console.print(f"[dim]{count} queue(s) found[/dim]")


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] sqs get-config <queue-url>")
        return
    client = session_manager.client("sqs")
    response = client.get_queue_attributes(
        QueueUrl=args[0],
        AttributeNames=["All"],
    )
    print_json(response.get("Attributes", {}))


def describe_queue(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] sqs describe-queue <queue-url>")
        return
    client = session_manager.client("sqs")
    response = client.get_queue_attributes(
        QueueUrl=args[0],
        AttributeNames=["All"],
    )
    print_json(response.get("Attributes", {}))


def get_queue_attributes(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] sqs get-queue-attributes <queue-url>")
        return
    client = session_manager.client("sqs")
    response = client.get_queue_attributes(
        QueueUrl=args[0],
        AttributeNames=["All"],
    )
    print_json(response.get("Attributes", {}))
