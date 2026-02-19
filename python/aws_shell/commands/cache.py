"""Cache commands — covers traditional ElastiCache clusters, replication groups, and serverless caches."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("cache", handle_cache, "Cache commands (ElastiCache)")


def handle_cache(args, config, session_manager):
    subcommands = {
        "list": list_all,
        "list-clusters": list_clusters,
        "list-replication-groups": list_replication_groups,
        "list-serverless": list_serverless,
        "describe": describe,
        "get-config": get_config,
    }
    subcommand_dispatch("cache", subcommands, args, config, session_manager)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _status_display(status):
    """Colorize common cache statuses."""
    return {
        "available": "[green]available[/green]",
        "creating": "[yellow]creating[/yellow]",
        "deleting": "[red]deleting[/red]",
        "modifying": "[yellow]modifying[/yellow]",
    }.get(status, status)


# ---------------------------------------------------------------------------
# list  — unified view of all cache types
# ---------------------------------------------------------------------------

def list_all(args, config, session_manager):
    client = session_manager.client("elasticache")

    table = Table(title=f"Caches — All Types ({config.region})")
    table.add_column("Name / ID", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Engine", style="green")
    table.add_column("Engine Version")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="yellow")

    count = 0

    # Traditional clusters
    try:
        for page in client.get_paginator("describe_cache_clusters").paginate():
            for c in page.get("CacheClusters", []):
                table.add_row(
                    c.get("CacheClusterId", ""),
                    "Cluster",
                    c.get("Engine", ""),
                    c.get("EngineVersion", ""),
                    _status_display(c.get("CacheClusterStatus", "")),
                    c.get("CacheNodeType", ""),
                )
                count += 1
    except Exception:
        pass

    # Replication groups
    try:
        for page in client.get_paginator("describe_replication_groups").paginate():
            for g in page.get("ReplicationGroups", []):
                members = len(g.get("MemberClusters", []))
                table.add_row(
                    g.get("ReplicationGroupId", ""),
                    "Replication Group",
                    "",
                    "",
                    _status_display(g.get("Status", "")),
                    f"{members} member(s)",
                )
                count += 1
    except Exception:
        pass

    # Serverless caches
    try:
        resp = client.describe_serverless_caches()
        for sc in resp.get("ServerlessCaches", []):
            table.add_row(
                sc.get("ServerlessCacheName", ""),
                "Serverless",
                sc.get("Engine", ""),
                sc.get("MajorEngineVersion", ""),
                _status_display(sc.get("Status", "")),
                sc.get("ServerlessCacheConfiguration", {}).get("DataStorage", {}).get("Maximum", "")
                    if isinstance(sc.get("ServerlessCacheConfiguration"), dict) else "",
            )
            count += 1
    except Exception:
        pass

    console.print(table)
    console.print(f"[dim]{count} cache(s) found[/dim]")


# ---------------------------------------------------------------------------
# list-clusters  — traditional cache clusters only
# ---------------------------------------------------------------------------

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
            table.add_row(
                cluster.get("CacheClusterId", ""),
                cluster.get("Engine", ""),
                cluster.get("EngineVersion", ""),
                cluster.get("CacheNodeType", ""),
                _status_display(cluster.get("CacheClusterStatus", "")),
                str(cluster.get("NumCacheNodes", 0)),
            )
            count += 1

    console.print(table)
    console.print(f"[dim]{count} cluster(s) found[/dim]")


# ---------------------------------------------------------------------------
# list-replication-groups
# ---------------------------------------------------------------------------

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
            members = group.get("MemberClusters", [])
            table.add_row(
                group.get("ReplicationGroupId", ""),
                group.get("Description", ""),
                _status_display(group.get("Status", "")),
                str(group.get("ClusterEnabled", False)),
                str(len(members)),
            )
            count += 1

    console.print(table)
    console.print(f"[dim]{count} replication group(s) found[/dim]")


# ---------------------------------------------------------------------------
# list-serverless  — serverless caches only
# ---------------------------------------------------------------------------

def list_serverless(args, config, session_manager):
    client = session_manager.client("elasticache")

    table = Table(title=f"ElastiCache Serverless Caches ({config.region})")
    table.add_column("Name", style="cyan")
    table.add_column("Engine", style="green")
    table.add_column("Major Version")
    table.add_column("Status", style="bold")
    table.add_column("ARN", style="dim")

    count = 0
    try:
        resp = client.describe_serverless_caches()
        for sc in resp.get("ServerlessCaches", []):
            table.add_row(
                sc.get("ServerlessCacheName", ""),
                sc.get("Engine", ""),
                sc.get("MajorEngineVersion", ""),
                _status_display(sc.get("Status", "")),
                sc.get("ARN", ""),
            )
            count += 1
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")

    console.print(table)
    console.print(f"[dim]{count} serverless cache(s) found[/dim]")


# ---------------------------------------------------------------------------
# describe  — tries serverless first, then cluster, then replication group
# ---------------------------------------------------------------------------

def describe(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] cache describe <cache-id>")
        return

    cache_id = args[0]
    client = session_manager.client("elasticache")

    # Try serverless first
    try:
        resp = client.describe_serverless_caches(ServerlessCacheName=cache_id)
        caches = resp.get("ServerlessCaches", [])
        if caches:
            print_json(caches[0] if len(caches) == 1 else caches)
            return
    except client.exceptions.ServerlessCacheNotFoundFault:
        pass
    except Exception:
        pass

    # Try traditional cluster
    try:
        resp = client.describe_cache_clusters(CacheClusterId=cache_id, ShowCacheNodeInfo=True)
        clusters = resp.get("CacheClusters", [])
        if clusters:
            print_json(clusters[0] if len(clusters) == 1 else clusters)
            return
    except client.exceptions.CacheClusterNotFoundFault:
        pass
    except Exception:
        pass

    # Try replication group
    try:
        resp = client.describe_replication_groups(ReplicationGroupId=cache_id)
        groups = resp.get("ReplicationGroups", [])
        if groups:
            print_json(groups[0] if len(groups) == 1 else groups)
            return
    except client.exceptions.ReplicationGroupNotFoundFault:
        pass
    except Exception:
        pass

    console.print(f"[red]Cache not found:[/red] {cache_id}")


# ---------------------------------------------------------------------------
# get-config  — same lookup order as describe
# ---------------------------------------------------------------------------

def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] cache get-config <cache-id>")
        return

    # Re-use describe — both return full JSON
    describe(args, config, session_manager)
