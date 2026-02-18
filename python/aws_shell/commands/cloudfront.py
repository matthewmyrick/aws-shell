"""CloudFront commands."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("cloudfront", handle_cloudfront, "CloudFront distribution commands")


def handle_cloudfront(args, config, session_manager):
    subcommands = {
        "list-distributions": list_distributions,
        "describe-distribution": describe_distribution,
        "get-config": get_config,
    }
    subcommand_dispatch("cloudfront", subcommands, args, config, session_manager)


def list_distributions(args, config, session_manager):
    client = session_manager.client("cloudfront")
    response = client.list_distributions()

    table = Table(title="CloudFront Distributions")
    table.add_column("ID", style="cyan")
    table.add_column("Domain Name", style="green")
    table.add_column("Status", style="bold")
    table.add_column("Enabled", style="yellow")
    table.add_column("Aliases")

    dist_list = response.get("DistributionList", {})
    for dist in dist_list.get("Items", []):
        aliases = dist.get("Aliases", {}).get("Items", [])
        status = dist.get("Status", "")
        status_display = {
            "Deployed": "[green]Deployed[/green]",
            "InProgress": "[yellow]InProgress[/yellow]",
        }.get(status, status)

        table.add_row(
            dist["Id"],
            dist.get("DomainName", ""),
            status_display,
            str(dist.get("Enabled", False)),
            ", ".join(aliases) if aliases else "",
        )
    console.print(table)


def describe_distribution(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] cloudfront describe-distribution <distribution-id>")
        return
    client = session_manager.client("cloudfront")
    response = client.get_distribution(Id=args[0])
    print_json(response.get("Distribution", {}))


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] cloudfront get-config <distribution-id>")
        return
    client = session_manager.client("cloudfront")
    response = client.get_distribution(Id=args[0])
    print_json(response.get("Distribution", {}))
