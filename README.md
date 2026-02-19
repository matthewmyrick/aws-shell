# aws-shell

An interactive shell for AWS with rich tables, tab completion, syntax highlighting, and a built-in Python REPL with boto3 pre-loaded.

## Installation

### Prerequisites

- Python 3.9+
- AWS credentials configured (`aws configure` or environment variables)

### Install locally

```bash
cd python
pip install -e .
```

This installs `aws-shell` as a CLI command. The `-e` flag enables editable mode so code changes take effect immediately.

### Run without installing

```bash
cd python
python -m aws_shell
```

## Usage

```bash
aws-shell
```

### Shell Commands

```
aws> ec2 list-instances            # Rich table of all EC2 instances
aws> s3 list-buckets               # List S3 buckets
aws> iam list-roles                # List IAM roles
aws> vpc list-vpcs                 # List VPCs
aws> lambda list-functions         # List Lambda functions
aws> help                          # See all available commands
aws> help ec2                      # Detailed help for a service
```

Every service supports `get-config <id>` to dump the full JSON config of a resource:

```
aws> ec2 get-config i-0abc123
aws> s3 get-config my-bucket
aws> rds get-config my-database
```

### Supported Services

ec2, vpc, s3, lambda, iam, sts, cfn, ses, sqs, rds, opensearch, route53, ga, cloudfront, cw, secrets, dynamodb, ssm, ecs, sso, elasticache, cognito

### Python REPL

Enter a Python REPL with all boto3 clients and helper methods pre-loaded:

```
aws> py
>>> ec2.list_instances()                          # Rich table output
>>> ec2.list_instances().filter(State="running")   # Filter rows (contains match)
>>> ec2.list_instances().filter(Name="web")        # Search by Name tag
>>> ec2.list_instances().find("production")        # Fuzzy search all fields
>>> ec2.list_instances().sort("Tags.Name")         # Sort by column
>>> ec2.list_instances().data                      # Raw list of dicts
>>> ec2.list_instances().json()                    # Pretty JSON output
>>> ec2.describe_instances(InstanceIds=["i-abc"])  # Direct boto3 calls work too
>>> find(some_data, "keyword")                     # Fuzzy search any data
```

### General Commands

```
aws> whoami                        # Show current AWS identity
aws> use-profile staging           # Switch AWS profile
aws> set-region us-west-2          # Switch region
aws> set-output json               # Set output format (table|json|text)
aws> services                      # List all available services
```

### Features

- Tab completion with descriptions for all commands and subcommands
- Syntax highlighting for commands, subcommands, strings, and ARNs
- Rich table output with color-coded columns and status values
- `ResourceTable` with `.filter()`, `.find()`, `.sort()`, `.select()` for exploring data
- Python REPL with all AWS clients and helper methods pre-loaded
- Command history across sessions
