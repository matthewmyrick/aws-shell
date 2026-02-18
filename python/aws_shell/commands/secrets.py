"""Secrets Manager commands (metadata only — NO secret values)."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("secrets", handle_secrets, "Secrets Manager commands (metadata only)")


def handle_secrets(args, config, session_manager):
    subcommands = {
        "list-secrets": list_secrets,
        "describe-secret": describe_secret,
        "get-config": get_config,
    }
    subcommand_dispatch("secrets", subcommands, args, config, session_manager)


def list_secrets(args, config, session_manager):
    client = session_manager.client("secretsmanager")
    paginator = client.get_paginator("list_secrets")

    table = Table(title=f"Secrets ({config.region})")
    table.add_column("Name", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Last Changed")
    table.add_column("Last Accessed")
    table.add_column("Rotation", style="yellow")

    count = 0
    for page in paginator.paginate():
        for secret in page.get("SecretList", []):
            table.add_row(
                secret.get("Name", ""),
                secret.get("Description", ""),
                str(secret.get("LastChangedDate", "")),
                str(secret.get("LastAccessedDate", "")),
                str(secret.get("RotationEnabled", False)),
            )
            count += 1

    console.print(table)
    console.print(f"[dim]{count} secret(s) found[/dim]")


def describe_secret(args, config, session_manager):
    """Show secret metadata only — never retrieves the secret value."""
    if not args:
        console.print("[yellow]Usage:[/yellow] secrets describe-secret <secret-name>")
        return
    client = session_manager.client("secretsmanager")
    response = client.describe_secret(SecretId=args[0])
    # Remove any fields that could leak values (defensive)
    response.pop("SecretString", None)
    response.pop("SecretBinary", None)
    response.pop("ResponseMetadata", None)
    print_json(response)


def get_config(args, config, session_manager):
    """Get secret metadata only — never retrieves the secret value."""
    if not args:
        console.print("[yellow]Usage:[/yellow] secrets get-config <secret-name>")
        return
    client = session_manager.client("secretsmanager")
    response = client.describe_secret(SecretId=args[0])
    response.pop("SecretString", None)
    response.pop("SecretBinary", None)
    response.pop("ResponseMetadata", None)
    print_json(response)
