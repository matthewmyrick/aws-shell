"""Route 53 commands."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("route53", handle_route53, "Route 53 DNS commands")


def handle_route53(args, config, session_manager):
    subcommands = {
        "list-hosted-zones": list_hosted_zones,
        "list-records": list_records,
        "get-config": get_config,
    }
    subcommand_dispatch("route53", subcommands, args, config, session_manager)


def list_hosted_zones(args, config, session_manager):
    client = session_manager.client("route53")
    response = client.list_hosted_zones()

    table = Table(title="Route 53 Hosted Zones")
    table.add_column("Zone ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Type", style="yellow")
    table.add_column("Record Count")

    for zone in response.get("HostedZones", []):
        zone_id = zone["Id"].split("/")[-1]
        zone_type = "Private" if zone.get("Config", {}).get("PrivateZone") else "Public"
        table.add_row(
            zone_id,
            zone["Name"],
            zone_type,
            str(zone.get("ResourceRecordSetCount", 0)),
        )
    console.print(table)


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] route53 get-config <zone-id>")
        return
    client = session_manager.client("route53")
    response = client.get_hosted_zone(Id=args[0])
    print_json(response)


def list_records(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] route53 list-records <hosted-zone-id>")
        return
    client = session_manager.client("route53")
    response = client.list_resource_record_sets(HostedZoneId=args[0])

    table = Table(title=f"DNS Records (Zone: {args[0]})")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("TTL", style="yellow")
    table.add_column("Values")

    for record in response.get("ResourceRecordSets", []):
        values = []
        for rr in record.get("ResourceRecords", []):
            values.append(rr.get("Value", ""))
        alias = record.get("AliasTarget", {})
        if alias:
            values.append(f"ALIAS -> {alias.get('DNSName', '')}")

        table.add_row(
            record["Name"],
            record["Type"],
            str(record.get("TTL", "")),
            "\n".join(values) if values else "",
        )
    console.print(table)
