"""SSO Admin commands."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("sso", handle_sso, "SSO Admin commands")


def handle_sso(args, config, session_manager):
    subcommands = {
        "list-instances": list_instances,
        "list-permission-sets": list_permission_sets,
        "get-config": get_config,
    }
    subcommand_dispatch("sso", subcommands, args, config, session_manager)


def list_instances(args, config, session_manager):
    client = session_manager.client("sso-admin")
    response = client.list_instances()

    table = Table(title="SSO Instances")
    table.add_column("Instance ARN", style="cyan")
    table.add_column("Identity Store ID", style="green")

    for instance in response.get("Instances", []):
        table.add_row(
            instance.get("InstanceArn", ""),
            instance.get("IdentityStoreId", ""),
        )
    console.print(table)


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] sso get-config <instance-arn>")
        return
    client = session_manager.client("sso-admin")
    response = client.list_permission_sets(InstanceArn=args[0])
    arns = response.get("PermissionSets", [])
    results = []
    for arn in arns:
        try:
            detail = client.describe_permission_set(
                InstanceArn=args[0], PermissionSetArn=arn
            )
            results.append(detail.get("PermissionSet", {}))
        except Exception:
            results.append({"PermissionSetArn": arn, "Error": "Could not describe"})
    print_json(results)


def list_permission_sets(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] sso list-permission-sets <instance-arn>")
        return
    client = session_manager.client("sso-admin")
    response = client.list_permission_sets(InstanceArn=args[0])

    arns = response.get("PermissionSets", [])
    if not arns:
        console.print("[dim]No permission sets found[/dim]")
        return

    table = Table(title="SSO Permission Sets")
    table.add_column("Permission Set ARN", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Description")
    table.add_column("Session Duration")

    for arn in arns:
        try:
            detail = client.describe_permission_set(
                InstanceArn=args[0], PermissionSetArn=arn
            )
            ps = detail.get("PermissionSet", {})
            table.add_row(
                arn,
                ps.get("Name", ""),
                ps.get("Description", ""),
                ps.get("SessionDuration", ""),
            )
        except Exception:
            table.add_row(arn, "", "", "")

    console.print(table)
