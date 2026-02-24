"""Auto-completion for AWS Shell with descriptions."""
from prompt_toolkit.completion import Completer, Completion

AWS_REGIONS = [
    "us-east-1", "us-east-2", "us-west-1", "us-west-2",
    "af-south-1",
    "ap-east-1", "ap-south-1", "ap-south-2",
    "ap-southeast-1", "ap-southeast-2", "ap-southeast-3",
    "ap-northeast-1", "ap-northeast-2", "ap-northeast-3",
    "ca-central-1",
    "eu-central-1", "eu-central-2",
    "eu-west-1", "eu-west-2", "eu-west-3",
    "eu-south-1", "eu-south-2",
    "eu-north-1",
    "me-south-1", "me-central-1",
    "sa-east-1",
]

OUTPUT_FORMATS = ["table", "json", "text"]

# Top-level command descriptions
COMMAND_DESCRIPTIONS = {
    "ec2": "EC2 instance management",
    "vpc": "VPC networking",
    "s3": "S3 bucket management",
    "lambda": "Lambda functions",
    "iam": "IAM management",
    "sts": "Security Token Service",
    "cfn": "CloudFormation stacks",
    "ses": "Simple Email Service",
    "sqs": "Simple Queue Service",
    "rds": "Relational Database Service",
    "opensearch": "OpenSearch Service",
    "route53": "Route 53 DNS",
    "ga": "Global Accelerator",
    "cloudfront": "CloudFront CDN",
    "cw": "CloudWatch Monitoring & Logs",
    "secrets": "Secrets Manager",
    "dynamodb": "DynamoDB",
    "ssm": "Systems Manager",
    "ecs": "Elastic Container Service",
    "sso": "SSO Admin",
    "cache": "Caching (ElastiCache)",
    "cognito": "Cognito User Pools",
    "kms": "Key Management Service",
    "search": "Fuzzy search resource configs",
    "help": "Show available commands",
    "py": "Python REPL",
    "python": "Python REPL",
    "exec": "Run Python expression",
    "login": "SSO login for current profile",
    "whoami": "Show current identity",
    "services": "List AWS services",
    "use-profile": "Switch AWS profile",
    "set-region": "Switch AWS region",
    "set-output": "Set output format",
    "clear": "Clear terminal",
    "exit": "Exit the shell",
    "quit": "Exit the shell",
    "ai": "Ask AI about AWS",
    "set-config": "Set a config value",
    "show-config": "Show all config values",
}

# Subcommand descriptions per service
SUBCOMMAND_DESCRIPTIONS = {
    "ec2": {
        "list-instances": "List all EC2 instances",
        "describe-instance": "Show detailed instance info",
        "start-instance": "Start a stopped instance",
        "stop-instance": "Stop a running instance",
        "get-config": "Get full instance config JSON",
    },
    "vpc": {
        "list-vpcs": "List all VPCs",
        "describe-vpc": "Show detailed VPC info",
        "list-subnets": "List subnets",
        "list-security-groups": "List security groups",
        "get-config": "Get full VPC config JSON",
    },
    "s3": {
        "list-buckets": "List all S3 buckets",
        "list-bucket-names": "List bucket names and ARNs",
        "list-objects": "List objects in a bucket",
        "get-config": "Get full bucket config JSON",
    },
    "lambda": {
        "list-functions": "List all Lambda functions",
        "describe-function": "Show function details",
        "invoke": "Invoke a Lambda function",
        "get-config": "Get full function config JSON",
    },
    "iam": {
        "list-users": "List all IAM users",
        "list-roles": "List all IAM roles",
        "list-policies": "List customer-managed policies",
        "get-config": "Get full role config JSON",
    },
    "sts": {
        "get-caller-identity": "Show current identity",
    },
    "cfn": {
        "list-stacks": "List CloudFormation stacks",
        "describe-stack": "Show stack details",
        "get-config": "Get full stack config JSON",
    },
    "ses": {
        "list-identities": "List email identities",
        "get-send-quota": "Show sending quota",
        "list-configuration-sets": "List configuration sets",
        "get-config": "Get full identity config JSON",
    },
    "sqs": {
        "list-queues": "List all SQS queues",
        "describe-queue": "Show queue attributes",
        "get-queue-attributes": "Get all queue attributes",
        "get-config": "Get full queue config JSON",
    },
    "rds": {
        "list-instances": "List all RDS instances",
        "describe-instance": "Show instance details",
        "list-clusters": "List Aurora clusters",
        "describe-cluster": "Show cluster details",
        "get-config": "Get full DB instance config JSON",
    },
    "opensearch": {
        "list-domains": "List OpenSearch domains",
        "describe-domain": "Show domain details",
        "get-config": "Get full domain config JSON",
    },
    "route53": {
        "list-hosted-zones": "List hosted zones",
        "list-records": "List DNS records in a zone",
        "get-config": "Get full hosted zone config JSON",
    },
    "ga": {
        "list-accelerators": "List global accelerators",
        "describe-accelerator": "Show accelerator details",
        "get-config": "Get full accelerator config JSON",
    },
    "cloudfront": {
        "list-distributions": "List distributions",
        "describe-distribution": "Show distribution details",
        "get-config": "Get full distribution config JSON",
    },
    "cw": {
        "list-alarms": "List CloudWatch alarms",
        "describe-alarm": "Show alarm details",
        "list-log-groups": "List log groups",
        "list-metrics": "List metrics",
        "get-config": "Get full alarm config JSON",
    },
    "secrets": {
        "list-secrets": "List all secrets",
        "describe-secret": "Show secret metadata (no values)",
        "get-config": "Get secret metadata JSON (no values)",
    },
    "dynamodb": {
        "list-tables": "List DynamoDB tables",
        "describe-table": "Show table details",
        "scan": "Scan table items",
        "get-config": "Get full table config JSON",
    },
    "ssm": {
        "list-parameters": "List SSM parameters",
        "get-parameter": "Get parameter value",
        "list-instances": "List managed instances",
        "get-config": "Get full parameter config JSON",
    },
    "ecs": {
        "list-clusters": "List ECS clusters",
        "describe-cluster": "Show cluster details",
        "list-services": "List services in a cluster",
        "list-tasks": "List tasks in a cluster",
        "get-config": "Get full cluster config JSON",
    },
    "sso": {
        "list-instances": "List SSO instances",
        "list-permission-sets": "List permission sets",
        "get-config": "Get permission set config JSON",
    },
    "cache": {
        "list": "List all caches (clusters, replication groups, serverless)",
        "list-clusters": "List traditional cache clusters",
        "list-replication-groups": "List replication groups",
        "list-serverless": "List serverless caches",
        "describe": "Describe a cache by ID (auto-detects type)",
        "get-config": "Get full cache config JSON",
    },
    "cognito": {
        "list-user-pools": "List user pools",
        "describe-user-pool": "Show user pool details",
        "list-users": "List users in a pool",
        "get-config": "Get full user pool config JSON",
    },
    "kms": {
        "list-keys": "List all KMS keys",
        "describe-key": "Show key details",
        "list-aliases": "List key aliases",
        "get-key-policy": "Show key policy",
        "get-public-key": "Download public key (asymmetric only)",
        "get-config": "Get full key config JSON",
    },
    "ai": {
        "clear": "Clear conversation history",
        "debug": "Debug last error with AI",
    },
    "help": {
        "ec2": "EC2 help",
        "vpc": "VPC help",
        "s3": "S3 help",
        "lambda": "Lambda help",
        "iam": "IAM help",
        "sts": "STS help",
        "cfn": "CloudFormation help",
        "ses": "SES help",
        "sqs": "SQS help",
        "rds": "RDS help",
        "opensearch": "OpenSearch help",
        "route53": "Route 53 help",
        "ga": "Global Accelerator help",
        "cloudfront": "CloudFront help",
        "cw": "CloudWatch help",
        "secrets": "Secrets Manager help",
        "dynamodb": "DynamoDB help",
        "ssm": "Systems Manager help",
        "ecs": "ECS help",
        "sso": "SSO help",
        "cache": "Cache help",
        "cognito": "Cognito help",
        "kms": "KMS help",
        "search": "Search help",
        "python": "Python REPL help",
        "general": "General commands help",
        "ai": "AI assistant help",
    },
}


class AWSShellCompleter(Completer):
    """Custom completer that provides descriptions alongside completions."""

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor.lstrip()
        parts = text.split()

        if not parts or (len(parts) == 1 and not text.endswith(" ")):
            # Completing the first word (top-level command)
            partial = parts[0].lower() if parts else ""
            for cmd, desc in COMMAND_DESCRIPTIONS.items():
                if cmd.startswith(partial):
                    yield Completion(
                        cmd,
                        start_position=-len(partial),
                        display_meta=desc,
                    )
        elif len(parts) >= 1:
            command = parts[0].lower()

            # Special cases
            if command == "set-region":
                partial = parts[1].lower() if len(parts) > 1 and not text.endswith(" ") else ""
                if text.endswith(" ") and len(parts) == 1:
                    partial = ""
                for region in AWS_REGIONS:
                    if region.startswith(partial):
                        yield Completion(
                            region,
                            start_position=-len(partial),
                            display_meta="AWS region",
                        )
                return

            if command == "set-output":
                partial = parts[1].lower() if len(parts) > 1 and not text.endswith(" ") else ""
                if text.endswith(" ") and len(parts) == 1:
                    partial = ""
                for fmt in OUTPUT_FORMATS:
                    if fmt.startswith(partial):
                        yield Completion(
                            fmt,
                            start_position=-len(partial),
                            display_meta="output format",
                        )
                return

            # Subcommand completion
            if command in SUBCOMMAND_DESCRIPTIONS:
                subcmds = SUBCOMMAND_DESCRIPTIONS[command]
                # Only complete the second word
                if len(parts) == 1 and text.endswith(" "):
                    partial = ""
                elif len(parts) == 2 and not text.endswith(" "):
                    partial = parts[1].lower()
                else:
                    return

                for sub, desc in subcmds.items():
                    if sub.startswith(partial):
                        yield Completion(
                            sub,
                            start_position=-len(partial),
                            display_meta=desc,
                        )


def build_completer(registry, session_manager):
    return AWSShellCompleter()
