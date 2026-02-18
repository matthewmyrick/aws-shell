"""ElastiCache commands."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("elasticache", handle_elasticache, "ElastiCache commands")


def handle_elasticache(args, config, session_manager):
    subcommands = {
        "list-clusters": list_clusters,
        "describe-cluster": describe_cluster,
        "list-replication-groups": list_replication_groups,
        "get-config": get_config,
    }
    subcommand_dispatch("elasticache", subcommands, args, config, session_manager)


def list_clusters(args, config, session_manager):
    client = session_manager.client("elasticache")
    paginator = client.get_paginator("describe_cache_clusters")

    table = Table(title=f"ElastiCache Clusters ({config.region})")
    table.add_column("Cluster ID", style="cyan")
    table.add_column("Engine", style="green")
    table.add_column("Engine Version")
    table.add_column("Node Type", style="yellow")
    table.add_column("Status", style="bold")
    table.add_column("Nodes")

    count = 0
    for page in paginator.paginate():
        for cluster in page.get("CacheClusters", []):
            status = cluster.get("CacheClusterStatus", "")
            status_display = {
                "available": "[green]available[/green]",
                "creating": "[yellow]creating[/yellow]",
                "deleting": "[red]deleting[/red]",
                "modifying": "[yellow]modifying[/yellow]",
            }.get(status, status)

            table.add_row(
                cluster.get("CacheClusterId", ""),
                cluster.get("Engine", ""),
                cluster.get("EngineVersion", ""),
                cluster.get("CacheNodeType", ""),
                status_display,
                str(cluster.get("NumCacheNodes", 0)),
            )
            count += 1

    console.print(table)
    console.print(f"[dim]{count} cluster(s) found[/dim]")


def describe_cluster(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] elasticache describe-cluster <cluster-id>")
        return
    client = session_manager.client("elasticache")
    response = client.describe_cache_clusters(
        CacheClusterId=args[0], ShowCacheNodeInfo=True
    )
    print_json(response.get("CacheClusters", []))


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] elasticache get-config <cluster-id>")
        return
    client = session_manager.client("elasticache")
    response = client.describe_cache_clusters(
        CacheClusterId=args[0], ShowCacheNodeInfo=True
    )
    print_json(response.get("CacheClusters", []))


def list_replication_groups(args, config, session_manager):
    client = session_manager.client("elasticache")
    paginator = client.get_paginator("describe_replication_groups")

    table = Table(title=f"ElastiCache Replication Groups ({config.region})")
    table.add_column("Replication Group ID", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Status", style="bold")
    table.add_column("Cluster Enabled", style="yellow")
    table.add_column("Members")

    count = 0
    for page in paginator.paginate():
        for group in page.get("ReplicationGroups", []):
            status = group.get("Status", "")
            status_display = {
                "available": "[green]available[/green]",
                "creating": "[yellow]creating[/yellow]",
                "deleting": "[red]deleting[/red]",
            }.get(status, status)

            members = group.get("MemberClusters", [])

            table.add_row(
                group.get("ReplicationGroupId", ""),
                group.get("Description", ""),
                status_display,
                str(group.get("ClusterEnabled", False)),
                str(len(members)),
            )
            count += 1

    console.print(table)
    console.print(f"[dim]{count} replication group(s) found[/dim]")
