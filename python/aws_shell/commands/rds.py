"""RDS (Relational Database Service) commands."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("rds", handle_rds, "RDS database commands")


def handle_rds(args, config, session_manager):
    subcommands = {
        "list-instances": list_instances,
        "describe-instance": describe_instance,
        "list-clusters": list_clusters,
        "describe-cluster": describe_cluster,
        "get-config": get_config,
    }
    subcommand_dispatch("rds", subcommands, args, config, session_manager)


def list_instances(args, config, session_manager):
    client = session_manager.client("rds")
    paginator = client.get_paginator("describe_db_instances")

    table = Table(title=f"RDS Instances ({config.region})")
    table.add_column("DB Instance ID", style="cyan")
    table.add_column("Engine", style="green")
    table.add_column("Status", style="bold")
    table.add_column("Class", style="yellow")
    table.add_column("Endpoint")
    table.add_column("Multi-AZ")

    count = 0
    for page in paginator.paginate():
        for db in page["DBInstances"]:
            status = db.get("DBInstanceStatus", "")
            status_display = {
                "available": "[green]available[/green]",
                "stopped": "[red]stopped[/red]",
                "creating": "[yellow]creating[/yellow]",
                "deleting": "[red]deleting[/red]",
                "modifying": "[yellow]modifying[/yellow]",
            }.get(status, status)

            endpoint = db.get("Endpoint", {})
            endpoint_str = f"{endpoint.get('Address', '')}:{endpoint.get('Port', '')}" if endpoint else ""

            table.add_row(
                db["DBInstanceIdentifier"],
                db.get("Engine", ""),
                status_display,
                db.get("DBInstanceClass", ""),
                endpoint_str,
                str(db.get("MultiAZ", False)),
            )
            count += 1

    console.print(table)
    console.print(f"[dim]{count} instance(s) found[/dim]")


def describe_instance(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] rds describe-instance <db-instance-id>")
        return
    client = session_manager.client("rds")
    response = client.describe_db_instances(DBInstanceIdentifier=args[0])
    print_json(response["DBInstances"])


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] rds get-config <db-instance-id>")
        return
    client = session_manager.client("rds")
    response = client.describe_db_instances(DBInstanceIdentifier=args[0])
    print_json(response["DBInstances"])


def list_clusters(args, config, session_manager):
    client = session_manager.client("rds")
    paginator = client.get_paginator("describe_db_clusters")

    table = Table(title=f"RDS Clusters ({config.region})")
    table.add_column("Cluster ID", style="cyan")
    table.add_column("Engine", style="green")
    table.add_column("Status", style="bold")
    table.add_column("Endpoint")
    table.add_column("Members")

    count = 0
    for page in paginator.paginate():
        for cluster in page["DBClusters"]:
            status = cluster.get("Status", "")
            status_display = {
                "available": "[green]available[/green]",
                "creating": "[yellow]creating[/yellow]",
                "deleting": "[red]deleting[/red]",
            }.get(status, status)

            table.add_row(
                cluster["DBClusterIdentifier"],
                cluster.get("Engine", ""),
                status_display,
                cluster.get("Endpoint", ""),
                str(len(cluster.get("DBClusterMembers", []))),
            )
            count += 1

    console.print(table)
    console.print(f"[dim]{count} cluster(s) found[/dim]")


def describe_cluster(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] rds describe-cluster <cluster-id>")
        return
    client = session_manager.client("rds")
    response = client.describe_db_clusters(DBClusterIdentifier=args[0])
    print_json(response["DBClusters"])
