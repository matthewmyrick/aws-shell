"""Help command."""
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

SERVICE_HELP = {
    "ec2": {
        "description": "EC2 instance management",
        "commands": {
            "ec2 list-instances": "List all EC2 instances in the current region",
            "ec2 describe-instance <id>": "Show detailed info for an instance",
            "ec2 start-instance <id>": "Start a stopped instance (requires confirmation)",
            "ec2 stop-instance <id>": "Stop a running instance (requires confirmation)",
            "ec2 get-config <id>": "Get full instance config as JSON",
        },
    },
    "vpc": {
        "description": "VPC networking",
        "commands": {
            "vpc list-vpcs": "List all VPCs in the current region",
            "vpc describe-vpc <vpc-id>": "Show detailed VPC info as JSON",
            "vpc list-subnets [vpc-id]": "List subnets (optionally filter by VPC)",
            "vpc list-security-groups [vpc-id]": "List security groups (optionally filter by VPC)",
            "vpc get-config <vpc-id>": "Get full VPC config as JSON",
        },
    },
    "s3": {
        "description": "S3 bucket and object management",
        "commands": {
            "s3 list-buckets": "List all S3 buckets with creation date",
            "s3 list-bucket-names": "List just bucket names and ARNs",
            "s3 list-objects <bucket>": "List objects in a bucket",
            "s3 get-config <bucket>": "Get full bucket config as JSON",
        },
    },
    "lambda": {
        "description": "Lambda function management",
        "commands": {
            "lambda list-functions": "List all Lambda functions",
            "lambda describe-function <name>": "Show detailed info for a function",
            "lambda invoke <name>": "Invoke a Lambda function",
            "lambda get-config <name>": "Get full function config as JSON",
        },
    },
    "iam": {
        "description": "IAM user, role, and policy management",
        "commands": {
            "iam list-users": "List all IAM users",
            "iam list-roles": "List all IAM roles",
            "iam list-policies": "List customer-managed policies",
            "iam get-config <role-name>": "Get full role config as JSON",
        },
    },
    "sts": {
        "description": "Security Token Service",
        "commands": {
            "sts get-caller-identity": "Show current authenticated identity",
        },
    },
    "cfn": {
        "description": "CloudFormation stack management",
        "commands": {
            "cfn list-stacks": "List all CloudFormation stacks",
            "cfn describe-stack <name>": "Show detailed stack info",
            "cfn get-config <name>": "Get full stack config as JSON",
        },
    },
    "ses": {
        "description": "Simple Email Service",
        "commands": {
            "ses list-identities": "List email identities (domains/addresses)",
            "ses get-send-quota": "Show sending quota and limits",
            "ses list-configuration-sets": "List configuration sets",
            "ses get-config <identity>": "Get full identity config as JSON",
        },
    },
    "sqs": {
        "description": "Simple Queue Service",
        "commands": {
            "sqs list-queues": "List all SQS queues",
            "sqs describe-queue <url>": "Show queue attributes",
            "sqs get-queue-attributes <url>": "Get all queue attributes",
            "sqs get-config <url>": "Get full queue config as JSON",
        },
    },
    "rds": {
        "description": "Relational Database Service",
        "commands": {
            "rds list-instances": "List all RDS instances",
            "rds describe-instance <id>": "Show instance details",
            "rds list-clusters": "List all Aurora clusters",
            "rds describe-cluster <id>": "Show cluster details",
            "rds get-config <id>": "Get full DB instance config as JSON",
        },
    },
    "opensearch": {
        "description": "OpenSearch Service",
        "commands": {
            "opensearch list-domains": "List all OpenSearch domains",
            "opensearch describe-domain <name>": "Show domain details",
            "opensearch get-config <name>": "Get full domain config as JSON",
        },
    },
    "route53": {
        "description": "Route 53 DNS",
        "commands": {
            "route53 list-hosted-zones": "List all hosted zones",
            "route53 list-records <zone-id>": "List DNS records in a zone",
            "route53 get-config <zone-id>": "Get full hosted zone config as JSON",
        },
    },
    "ga": {
        "description": "Global Accelerator",
        "commands": {
            "ga list-accelerators": "List all global accelerators",
            "ga describe-accelerator <arn>": "Show accelerator details",
            "ga get-config <arn>": "Get full accelerator config as JSON",
        },
    },
    "cloudfront": {
        "description": "CloudFront CDN",
        "commands": {
            "cloudfront list-distributions": "List all distributions",
            "cloudfront describe-distribution <id>": "Show distribution details",
            "cloudfront get-config <id>": "Get full distribution config as JSON",
        },
    },
    "cw": {
        "description": "CloudWatch Monitoring & Logs",
        "commands": {
            "cw list-alarms": "List all CloudWatch alarms",
            "cw describe-alarm <name>": "Show alarm details",
            "cw list-log-groups": "List CloudWatch log groups",
            "cw list-metrics [namespace]": "List metrics (optionally filter by namespace)",
            "cw get-config <name>": "Get full alarm config as JSON",
        },
    },
    "secrets": {
        "description": "Secrets Manager (metadata only)",
        "commands": {
            "secrets list-secrets": "List all secrets",
            "secrets describe-secret <name>": "Show secret metadata (no values)",
            "secrets get-config <name>": "Get secret metadata as JSON (no values)",
        },
    },
    "dynamodb": {
        "description": "DynamoDB",
        "commands": {
            "dynamodb list-tables": "List all DynamoDB tables",
            "dynamodb describe-table <name>": "Show table details",
            "dynamodb scan <table> [limit]": "Scan table items (default limit: 10)",
            "dynamodb get-config <name>": "Get full table config as JSON",
        },
    },
    "ssm": {
        "description": "Systems Manager",
        "commands": {
            "ssm list-parameters": "List all SSM parameters",
            "ssm get-parameter <name>": "Get parameter value",
            "ssm list-instances": "List SSM managed instances",
            "ssm get-config <name>": "Get full parameter config as JSON",
        },
    },
    "ecs": {
        "description": "Elastic Container Service",
        "commands": {
            "ecs list-clusters": "List all ECS clusters",
            "ecs describe-cluster <name>": "Show cluster details",
            "ecs list-services <cluster>": "List services in a cluster",
            "ecs list-tasks <cluster>": "List tasks in a cluster",
            "ecs get-config <name>": "Get full cluster config as JSON",
        },
    },
    "sso": {
        "description": "SSO Admin",
        "commands": {
            "sso list-instances": "List SSO instances",
            "sso list-permission-sets <arn>": "List permission sets for an instance",
            "sso get-config <instance-arn>": "Get permission set configs as JSON",
        },
    },
    "elasticache": {
        "description": "ElastiCache",
        "commands": {
            "elasticache list-clusters": "List all cache clusters",
            "elasticache describe-cluster <id>": "Show cluster details",
            "elasticache list-replication-groups": "List replication groups",
            "elasticache get-config <id>": "Get full cluster config as JSON",
        },
    },
    "cognito": {
        "description": "Cognito User Pools",
        "commands": {
            "cognito list-user-pools": "List all user pools",
            "cognito describe-user-pool <id>": "Show user pool details",
            "cognito list-users <pool-id>": "List users in a pool",
            "cognito get-config <pool-id>": "Get full user pool config as JSON",
        },
    },
    "search": {
        "description": "Fuzzy search through resource configs",
        "commands": {
            "search <service> <id> <keyword>": "Search a resource's config for a keyword",
        },
    },
    "python": {
        "description": "Python REPL with boto3 pre-loaded",
        "commands": {
            "py": "Enter interactive Python REPL (clients + helpers pre-loaded)",
            "python": "Alias for py",
            "exec <expression>": "Execute a single Python expression and print result",
            ">>> ec2.list_instances()": "Rich table of EC2 instances",
            ">>> s3.list_buckets()": "Rich table of S3 buckets",
            ">>> iam.list_roles()": "Rich table of IAM roles",
            ">>> .filter(State='running')": "Filter table rows",
            ">>> .find('keyword')": "Fuzzy search table rows",
            ">>> .sort('Name')": "Sort table by column",
            ">>> .data": "Get raw list of dicts",
            ">>> find(data, kw)": "Fuzzy search through any JSON data",
        },
    },
    "general": {
        "description": "General shell commands",
        "commands": {
            "whoami": "Show current AWS identity",
            "services": "List all available AWS services",
            "use-profile <name>": "Switch AWS profile",
            "set-region <region>": "Switch AWS region",
            "set-output <format>": "Set output format (table|json|text)",
            "clear": "Clear the terminal",
            "exit / quit": "Exit the shell",
        },
    },
}


def register(registry):
    registry.register("help", cmd_help, "Show available commands")


def cmd_help(args, config, session_manager):
    if args:
        service = args[0].lower()
        if service in SERVICE_HELP:
            _show_service_help(service)
        else:
            console.print(
                f"[red]No help for:[/red] {service}\n"
                f"Available: {', '.join(SERVICE_HELP.keys())}"
            )
        return

    table = Table(title="AWS Shell Commands")
    table.add_column("Service", style="bold cyan", min_width=10)
    table.add_column("Description", style="white")
    table.add_column("Example", style="dim")

    table.add_row("ec2", "EC2 instance management", "ec2 list-instances")
    table.add_row("vpc", "VPC networking", "vpc list-vpcs")
    table.add_row("s3", "S3 bucket management", "s3 list-buckets")
    table.add_row("lambda", "Lambda functions", "lambda list-functions")
    table.add_row("iam", "IAM management", "iam list-users")
    table.add_row("sts", "Security Token Service", "sts get-caller-identity")
    table.add_row("cfn", "CloudFormation stacks", "cfn list-stacks")
    table.add_row("ses", "Simple Email Service", "ses list-identities")
    table.add_row("sqs", "Simple Queue Service", "sqs list-queues")
    table.add_row("rds", "Relational Database Service", "rds list-instances")
    table.add_row("opensearch", "OpenSearch Service", "opensearch list-domains")
    table.add_row("route53", "Route 53 DNS", "route53 list-hosted-zones")
    table.add_row("ga", "Global Accelerator", "ga list-accelerators")
    table.add_row("cloudfront", "CloudFront CDN", "cloudfront list-distributions")
    table.add_row("cw", "CloudWatch Monitoring & Logs", "cw list-alarms")
    table.add_row("secrets", "Secrets Manager", "secrets list-secrets")
    table.add_row("dynamodb", "DynamoDB", "dynamodb list-tables")
    table.add_row("ssm", "Systems Manager", "ssm list-parameters")
    table.add_row("ecs", "Elastic Container Service", "ecs list-clusters")
    table.add_row("sso", "SSO Admin", "sso list-instances")
    table.add_row("elasticache", "ElastiCache", "elasticache list-clusters")
    table.add_row("cognito", "Cognito User Pools", "cognito list-user-pools")
    table.add_row("", "", "")
    table.add_row("search", "Fuzzy search resource configs", "search ec2 i-abc subnet")
    table.add_row("", "", "")
    table.add_row("py / python", "Python REPL (boto3 pre-loaded)", "py")
    table.add_row("exec", "Run a Python expression", "exec s3.list_buckets()")
    table.add_row("", "", "")
    table.add_row("whoami", "Show current identity", "whoami")
    table.add_row("services", "List AWS services", "services")
    table.add_row("use-profile", "Switch AWS profile", "use-profile staging")
    table.add_row("set-region", "Switch AWS region", "set-region us-west-2")
    table.add_row("set-output", "Set output format", "set-output json")
    table.add_row("clear", "Clear terminal", "clear")
    table.add_row("exit", "Exit the shell", "exit")

    console.print(table)
    console.print(
        "\n[dim]Type [bold]help <service>[/bold] for detailed command info. "
        "Press [bold]Tab[/bold] for auto-completion.[/dim]"
    )


def _show_service_help(service):
    info = SERVICE_HELP[service]
    table = Table(title=f"{service.upper()} - {info['description']}")
    table.add_column("Command", style="bold cyan", min_width=35)
    table.add_column("Description", style="white")

    for cmd, desc in info["commands"].items():
        table.add_row(cmd, desc)

    console.print(table)
