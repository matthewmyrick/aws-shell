"""Cognito User Pools commands."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("cognito", handle_cognito, "Cognito user pool commands")


def handle_cognito(args, config, session_manager):
    subcommands = {
        "list-user-pools": list_user_pools,
        "describe-user-pool": describe_user_pool,
        "list-users": list_users,
        "get-config": get_config,
    }
    subcommand_dispatch("cognito", subcommands, args, config, session_manager)


def list_user_pools(args, config, session_manager):
    client = session_manager.client("cognito-idp")
    response = client.list_user_pools(MaxResults=60)

    table = Table(title=f"Cognito User Pools ({config.region})")
    table.add_column("Pool ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Status", style="bold")
    table.add_column("Created")
    table.add_column("Last Modified")

    for pool in response.get("UserPools", []):
        table.add_row(
            pool.get("Id", ""),
            pool.get("Name", ""),
            pool.get("Status", ""),
            str(pool.get("CreationDate", "")),
            str(pool.get("LastModifiedDate", "")),
        )
    console.print(table)


def describe_user_pool(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] cognito describe-user-pool <pool-id>")
        return
    client = session_manager.client("cognito-idp")
    response = client.describe_user_pool(UserPoolId=args[0])
    print_json(response.get("UserPool", {}))


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] cognito get-config <pool-id>")
        return
    client = session_manager.client("cognito-idp")
    response = client.describe_user_pool(UserPoolId=args[0])
    print_json(response.get("UserPool", {}))


def list_users(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] cognito list-users <pool-id>")
        return
    client = session_manager.client("cognito-idp")
    response = client.list_users(UserPoolId=args[0])

    table = Table(title=f"Cognito Users (Pool: {args[0]})")
    table.add_column("Username", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Enabled", style="yellow")
    table.add_column("Created")
    table.add_column("Email")

    for user in response.get("Users", []):
        status = user.get("UserStatus", "")
        status_display = {
            "CONFIRMED": "[green]CONFIRMED[/green]",
            "UNCONFIRMED": "[yellow]UNCONFIRMED[/yellow]",
            "FORCE_CHANGE_PASSWORD": "[yellow]FORCE_CHANGE_PASSWORD[/yellow]",
            "DISABLED": "[red]DISABLED[/red]",
        }.get(status, status)

        email = ""
        for attr in user.get("Attributes", []):
            if attr["Name"] == "email":
                email = attr["Value"]

        table.add_row(
            user.get("Username", ""),
            status_display,
            str(user.get("Enabled", False)),
            str(user.get("UserCreateDate", "")),
            email,
        )
    console.print(table)
