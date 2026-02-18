"""S3 commands."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("s3", handle_s3, "S3 bucket and object management")


def handle_s3(args, config, session_manager):
    subcommands = {
        "list-buckets": list_buckets,
        "list-bucket-names": list_bucket_names,
        "list-objects": list_objects,
        "get-config": get_config,
    }
    subcommand_dispatch("s3", subcommands, args, config, session_manager)


def list_buckets(args, config, session_manager):
    s3 = session_manager.client("s3")
    response = s3.list_buckets()

    table = Table(title="S3 Buckets")
    table.add_column("Bucket Name", style="cyan")
    table.add_column("Creation Date", style="green")

    for bucket in response.get("Buckets", []):
        table.add_row(
            bucket["Name"],
            str(bucket.get("CreationDate", "")),
        )

    console.print(table)
    console.print(f"[dim]{len(response.get('Buckets', []))} bucket(s) found[/dim]")


def list_bucket_names(args, config, session_manager):
    s3 = session_manager.client("s3")
    response = s3.list_buckets()

    table = Table(title="S3 Bucket Names")
    table.add_column("Bucket Name", style="cyan")
    table.add_column("ARN", style="dim")

    for bucket in response.get("Buckets", []):
        name = bucket["Name"]
        arn = bucket.get("BucketArn", f"arn:aws:s3:::{name}")
        table.add_row(name, arn)

    console.print(table)
    console.print(f"[dim]{len(response.get('Buckets', []))} bucket(s)[/dim]")


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] s3 get-config <bucket-name>")
        return
    s3 = session_manager.client("s3")
    result = {}
    try:
        loc = s3.get_bucket_location(Bucket=args[0])
        result["Location"] = loc.get("LocationConstraint", "us-east-1")
    except Exception as e:
        result["Location"] = f"Error: {e}"
    try:
        ver = s3.get_bucket_versioning(Bucket=args[0])
        result["Versioning"] = ver.get("Status", "Disabled")
        result["MFADelete"] = ver.get("MFADelete", "Disabled")
    except Exception as e:
        result["Versioning"] = f"Error: {e}"
    try:
        enc = s3.get_bucket_encryption(Bucket=args[0])
        result["Encryption"] = enc.get("ServerSideEncryptionConfiguration", {})
    except s3.exceptions.ClientError:
        result["Encryption"] = "None"
    except Exception as e:
        result["Encryption"] = f"Error: {e}"
    print_json(result)


def list_objects(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] s3 list-objects <bucket-name> [prefix]")
        return

    bucket = args[0]
    prefix = args[1] if len(args) > 1 else ""

    s3 = session_manager.client("s3")
    paginator = s3.get_paginator("list_objects_v2")

    table = Table(title=f"Objects in s3://{bucket}/{prefix}")
    table.add_column("Key", style="cyan")
    table.add_column("Size", style="yellow", justify="right")
    table.add_column("Last Modified", style="green")
    table.add_column("Storage Class")

    count = 0
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            size = obj.get("Size", 0)
            if size >= 1_073_741_824:
                size_str = f"{size / 1_073_741_824:.1f} GB"
            elif size >= 1_048_576:
                size_str = f"{size / 1_048_576:.1f} MB"
            elif size >= 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} B"

            table.add_row(
                obj["Key"],
                size_str,
                str(obj.get("LastModified", "")),
                obj.get("StorageClass", ""),
            )
            count += 1

    console.print(table)
    console.print(f"[dim]{count} object(s) found[/dim]")
