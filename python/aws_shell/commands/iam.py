"""IAM commands."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("iam", handle_iam, "IAM user, role, and policy management")


def handle_iam(args, config, session_manager):
    subcommands = {
        "list-users": list_users,
        "list-roles": list_roles,
        "list-policies": list_policies,
        "get-config": get_config,
    }
    subcommand_dispatch("iam", subcommands, args, config, session_manager)


def list_users(args, config, session_manager):
    iam = session_manager.client("iam")
    paginator = iam.get_paginator("list_users")

    table = Table(title="IAM Users")
    table.add_column("User Name", style="cyan")
    table.add_column("User ID", style="dim")
    table.add_column("ARN")
    table.add_column("Created", style="green")
    table.add_column("Password Last Used")

    count = 0
    for page in paginator.paginate():
        for user in page["Users"]:
            table.add_row(
                user["UserName"],
                user["UserId"],
                user["Arn"],
                str(user.get("CreateDate", "")),
                str(user.get("PasswordLastUsed", "N/A")),
            )
            count += 1

    console.print(table)
    console.print(f"[dim]{count} user(s) found[/dim]")


def list_roles(args, config, session_manager):
    iam = session_manager.client("iam")
    paginator = iam.get_paginator("list_roles")

    table = Table(title="IAM Roles")
    table.add_column("Role Name", style="cyan")
    table.add_column("Role ID", style="dim")
    table.add_column("Created", style="green")
    table.add_column("Description", max_width=50)

    count = 0
    for page in paginator.paginate():
        for role in page["Roles"]:
            table.add_row(
                role["RoleName"],
                role["RoleId"],
                str(role.get("CreateDate", "")),
                role.get("Description", "")[:50],
            )
            count += 1

    console.print(table)
    console.print(f"[dim]{count} role(s) found[/dim]")


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] iam get-config <role-name>")
        return
    iam = session_manager.client("iam")
    response = iam.get_role(RoleName=args[0])
    print_json(response.get("Role", {}))


def list_policies(args, config, session_manager):
    iam = session_manager.client("iam")
    paginator = iam.get_paginator("list_policies")

    table = Table(title="IAM Policies (Customer Managed)")
    table.add_column("Policy Name", style="cyan")
    table.add_column("Policy ID", style="dim")
    table.add_column("ARN")
    table.add_column("Attachment Count", justify="right")
    table.add_column("Created", style="green")

    count = 0
    for page in paginator.paginate(Scope="Local"):
        for policy in page["Policies"]:
            table.add_row(
                policy["PolicyName"],
                policy["PolicyId"],
                policy["Arn"],
                str(policy.get("AttachmentCount", 0)),
                str(policy.get("CreateDate", "")),
            )
            count += 1

    console.print(table)
    console.print(f"[dim]{count} policy(ies) found[/dim]")
