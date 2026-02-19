"""Syntax highlighting lexer for AWS Shell."""
from pygments.lexer import RegexLexer
from pygments.token import Keyword, Name, String, Text

# Only highlight actual known subcommands, not arbitrary hyphenated words
SUBCOMMANDS = (
    "list-instances", "describe-instance", "start-instance", "stop-instance",
    "list-security-groups", "list-vpcs", "describe-vpc", "list-subnets",
    "list-buckets", "list-bucket-names", "list-objects",
    "list-functions", "describe-function",
    "list-users", "list-roles", "list-policies",
    "get-caller-identity",
    "list-stacks", "describe-stack",
    "list-identities", "get-send-quota", "list-configuration-sets",
    "list-queues", "describe-queue", "get-queue-attributes",
    "list-clusters", "describe-cluster",
    "list-domains", "describe-domain",
    "list-hosted-zones", "list-records",
    "list-accelerators", "describe-accelerator",
    "list-distributions", "describe-distribution",
    "list-alarms", "describe-alarm", "list-log-groups", "list-metrics",
    "list-secrets", "describe-secret",
    "list-tables", "describe-table", "scan",
    "list-parameters", "get-parameter",
    "list-services", "list-tasks",
    "list-permission-sets",
    "list-replication-groups", "list-serverless",
    "list-user-pools", "describe-user-pool",
    "get-config",
    "use-profile", "set-region", "set-output",
)

COMMANDS = (
    "ec2", "vpc", "s3", "lambda", "iam", "sts", "cfn",
    "ses", "sqs", "rds", "opensearch", "route53",
    "ga", "cloudfront", "cw", "secrets", "dynamodb",
    "ssm", "ecs", "sso", "cache", "cognito",
    "search", "ai",
    "help", "whoami", "clear", "exit", "quit", "services",
    "py", "python", "exec",
    "set-config", "show-config",
)


class AWSShellLexer(RegexLexer):
    name = "AWSShell"
    aliases = ["awsshell"]

    tokens = {
        "root": [
            # Known commands — not when part of a hyphenated ID like vpc-f741219c
            (r"(?<![\w-])(" + "|".join(COMMANDS) + r")(?![\w-])", Keyword),
            # Known subcommands — same boundary protection
            (r"(?<![\w-])(" + "|".join(SUBCOMMANDS) + r")(?![\w-])", Name.Function),
            # Quoted strings
            (r'"[^"]*"', String),
            (r"'[^']*'", String),
            # ARN identifiers
            (r"arn:[^\s]+", String.Other),
            # Everything else is plain text (bucket names, IDs, numbers, etc.)
            (r"\s+", Text),
            (r".", Text),
        ]
    }
