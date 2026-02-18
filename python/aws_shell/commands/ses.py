"""SES (Simple Email Service) commands."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("ses", handle_ses, "SES email service commands")


def handle_ses(args, config, session_manager):
    subcommands = {
        "list-identities": list_identities,
        "get-send-quota": get_send_quota,
        "list-configuration-sets": list_configuration_sets,
        "get-config": get_config,
    }
    subcommand_dispatch("ses", subcommands, args, config, session_manager)


def list_identities(args, config, session_manager):
    client = session_manager.client("sesv2")
    response = client.list_email_identities()

    table = Table(title=f"SES Email Identities ({config.region})")
    table.add_column("Identity", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("Sending Enabled", style="yellow")

    for identity in response.get("EmailIdentities", []):
        table.add_row(
            identity.get("IdentityName", ""),
            identity.get("IdentityType", ""),
            str(identity.get("SendingEnabled", False)),
        )
    console.print(table)


def get_send_quota(args, config, session_manager):
    client = session_manager.client("sesv2")
    response = client.get_account()
    quota = response.get("SendQuota", {})
    print_json(quota)


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] ses get-config <email-identity>")
        return
    client = session_manager.client("sesv2")
    response = client.get_email_identity(EmailIdentity=args[0])
    print_json(response)


def list_configuration_sets(args, config, session_manager):
    client = session_manager.client("sesv2")
    response = client.list_configuration_sets()

    table = Table(title=f"SES Configuration Sets ({config.region})")
    table.add_column("Configuration Set Name", style="cyan")

    for name in response.get("ConfigurationSets", []):
        table.add_row(name)
    console.print(table)
