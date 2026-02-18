"""OpenSearch commands."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("opensearch", handle_opensearch, "OpenSearch domain commands")


def handle_opensearch(args, config, session_manager):
    subcommands = {
        "list-domains": list_domains,
        "describe-domain": describe_domain,
        "get-config": get_config,
    }
    subcommand_dispatch("opensearch", subcommands, args, config, session_manager)


def list_domains(args, config, session_manager):
    client = session_manager.client("opensearch")
    response = client.list_domain_names()

    table = Table(title=f"OpenSearch Domains ({config.region})")
    table.add_column("Domain Name", style="cyan")
    table.add_column("Engine Type", style="green")

    for domain in response.get("DomainNames", []):
        table.add_row(
            domain.get("DomainName", ""),
            domain.get("EngineType", ""),
        )
    console.print(table)


def describe_domain(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] opensearch describe-domain <domain-name>")
        return
    client = session_manager.client("opensearch")
    response = client.describe_domain(DomainName=args[0])
    print_json(response.get("DomainStatus", {}))


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] opensearch get-config <domain-name>")
        return
    client = session_manager.client("opensearch")
    response = client.describe_domain(DomainName=args[0])
    print_json(response.get("DomainStatus", {}))
