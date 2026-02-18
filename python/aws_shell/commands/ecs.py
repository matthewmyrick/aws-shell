"""ECS (Elastic Container Service) commands."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("ecs", handle_ecs, "ECS container service commands")


def handle_ecs(args, config, session_manager):
    subcommands = {
        "list-clusters": list_clusters,
        "describe-cluster": describe_cluster,
        "list-services": list_services,
        "list-tasks": list_tasks,
        "get-config": get_config,
    }
    subcommand_dispatch("ecs", subcommands, args, config, session_manager)


def list_clusters(args, config, session_manager):
    client = session_manager.client("ecs")
    response = client.list_clusters()
    arns = response.get("clusterArns", [])

    if not arns:
        console.print("[dim]No ECS clusters found[/dim]")
        return

    details = client.describe_clusters(clusters=arns)

    table = Table(title=f"ECS Clusters ({config.region})")
    table.add_column("Cluster Name", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Running Tasks", style="green")
    table.add_column("Pending Tasks", style="yellow")
    table.add_column("Services")
    table.add_column("Instances")

    for cluster in details.get("clusters", []):
        status = cluster.get("status", "")
        status_display = {
            "ACTIVE": "[green]ACTIVE[/green]",
            "INACTIVE": "[red]INACTIVE[/red]",
            "PROVISIONING": "[yellow]PROVISIONING[/yellow]",
        }.get(status, status)

        table.add_row(
            cluster.get("clusterName", ""),
            status_display,
            str(cluster.get("runningTasksCount", 0)),
            str(cluster.get("pendingTasksCount", 0)),
            str(cluster.get("activeServicesCount", 0)),
            str(cluster.get("registeredContainerInstancesCount", 0)),
        )
    console.print(table)


def describe_cluster(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] ecs describe-cluster <cluster-name>")
        return
    client = session_manager.client("ecs")
    response = client.describe_clusters(clusters=[args[0]])
    print_json(response.get("clusters", []))


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] ecs get-config <cluster-name>")
        return
    client = session_manager.client("ecs")
    response = client.describe_clusters(clusters=[args[0]])
    print_json(response.get("clusters", []))


def list_services(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] ecs list-services <cluster-name>")
        return
    client = session_manager.client("ecs")
    response = client.list_services(cluster=args[0])
    arns = response.get("serviceArns", [])

    if not arns:
        console.print(f"[dim]No services found in cluster {args[0]}[/dim]")
        return

    details = client.describe_services(cluster=args[0], services=arns)

    table = Table(title=f"ECS Services ({args[0]})")
    table.add_column("Service Name", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Desired", style="yellow")
    table.add_column("Running", style="green")
    table.add_column("Launch Type")
    table.add_column("Task Definition")

    for svc in details.get("services", []):
        status = svc.get("status", "")
        status_display = {
            "ACTIVE": "[green]ACTIVE[/green]",
            "DRAINING": "[yellow]DRAINING[/yellow]",
            "INACTIVE": "[red]INACTIVE[/red]",
        }.get(status, status)

        task_def = svc.get("taskDefinition", "").split("/")[-1]

        table.add_row(
            svc.get("serviceName", ""),
            status_display,
            str(svc.get("desiredCount", 0)),
            str(svc.get("runningCount", 0)),
            svc.get("launchType", ""),
            task_def,
        )
    console.print(table)


def list_tasks(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] ecs list-tasks <cluster-name>")
        return
    client = session_manager.client("ecs")
    response = client.list_tasks(cluster=args[0])
    arns = response.get("taskArns", [])

    if not arns:
        console.print(f"[dim]No tasks found in cluster {args[0]}[/dim]")
        return

    details = client.describe_tasks(cluster=args[0], tasks=arns)

    table = Table(title=f"ECS Tasks ({args[0]})")
    table.add_column("Task ID", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Task Definition", style="green")
    table.add_column("Launch Type")
    table.add_column("CPU")
    table.add_column("Memory")

    for task in details.get("tasks", []):
        task_id = task.get("taskArn", "").split("/")[-1]
        status = task.get("lastStatus", "")
        status_display = {
            "RUNNING": "[green]RUNNING[/green]",
            "PENDING": "[yellow]PENDING[/yellow]",
            "STOPPED": "[red]STOPPED[/red]",
        }.get(status, status)

        task_def = task.get("taskDefinitionArn", "").split("/")[-1]

        table.add_row(
            task_id,
            status_display,
            task_def,
            task.get("launchType", ""),
            task.get("cpu", ""),
            task.get("memory", ""),
        )
    console.print(table)
