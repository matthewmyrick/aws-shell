"""Search command — fuzzy search through AWS resource configurations."""
from rich.console import Console
from rich.table import Table
from ..utils.search import fuzzy_search
from ..utils.output import print_json

console = Console()

# Map service names to describe functions
SERVICE_DESCRIBERS = {
    "ec2": ("ec2", "describe_instances", "InstanceIds", "Reservations"),
    "rds": ("rds", "describe_db_instances", "DBInstanceIdentifier", None),
    "s3": ("s3", "list_objects_v2", "Bucket", None),
    "lambda": ("lambda", "get_function", "FunctionName", None),
    "ecs": ("ecs", "describe_clusters", "clusters", None),
    "cloudfront": ("cloudfront", "get_distribution", "Id", None),
    "dynamodb": ("dynamodb", "describe_table", "TableName", "Table"),
    "opensearch": ("opensearch", "describe_domain", "DomainName", "DomainStatus"),
    "secrets": ("secretsmanager", "describe_secret", "SecretId", None),
    "ssm": ("ssm", "get_parameter", "Name", "Parameter"),
    "cache": ("elasticache", "describe_serverless_caches", "ServerlessCacheName", None),
    "cognito": ("cognito-idp", "describe_user_pool", "UserPoolId", "UserPool"),
    "route53": ("route53", "get_hosted_zone", "Id", None),
    "sqs": ("sqs", "get_queue_attributes", "QueueUrl", "Attributes"),
}


def register(registry):
    registry.register("search", cmd_search, "Fuzzy search through resource config")


def cmd_search(args, config, session_manager):
    if len(args) < 3:
        console.print(
            "[yellow]Usage:[/yellow] search <service> <resource-id> <keyword>\n"
            "[dim]Example: search ec2 i-abc123 subnet[/dim]\n"
            "[dim]Example: search rds mydb encryption[/dim]"
        )
        return

    service = args[0].lower()
    resource_id = args[1]
    keyword = args[2]

    if service not in SERVICE_DESCRIBERS:
        console.print(
            f"[red]Unsupported service:[/red] {service}\n"
            f"Available: {', '.join(sorted(SERVICE_DESCRIBERS.keys()))}"
        )
        return

    client_name, method_name, param_name, result_key = SERVICE_DESCRIBERS[service]

    try:
        client = session_manager.client(client_name)
        method = getattr(client, method_name)

        # Build the API call arguments
        if service == "ec2":
            response = method(**{param_name: [resource_id]})
        elif service == "ecs":
            response = method(**{param_name: [resource_id]})
        elif service == "sqs":
            response = method(QueueUrl=resource_id, AttributeNames=["All"])
        elif service == "rds":
            response = method(DBInstanceIdentifier=resource_id)
        elif service == "cache":
            # Try serverless first, fall back to traditional cluster
            try:
                response = client.describe_serverless_caches(ServerlessCacheName=resource_id)
            except Exception:
                response = client.describe_cache_clusters(CacheClusterId=resource_id, ShowCacheNodeInfo=True)
        else:
            response = method(**{param_name: resource_id})

        # Extract the relevant data
        data = response
        if result_key and result_key in data:
            data = data[result_key]

        # Remove metadata
        if isinstance(data, dict):
            data.pop("ResponseMetadata", None)

        results = fuzzy_search(data, keyword)

        if not results:
            console.print(f"[dim]No matches for '{keyword}' in {service} {resource_id}[/dim]")
            return

        table = Table(title=f"Search: '{keyword}' in {service} {resource_id}")
        table.add_column("Key Path", style="cyan")
        table.add_column("Value", style="green")

        for path, value in results:
            # Truncate long values for display
            display_value = value if len(value) <= 120 else value[:117] + "..."
            table.add_row(path, display_value)

        console.print(table)
        console.print(f"[dim]{len(results)} match(es) found[/dim]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
