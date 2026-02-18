"""VPC commands."""
from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("vpc", handle_vpc, "VPC networking commands")


def handle_vpc(args, config, session_manager):
    subcommands = {
        "list-vpcs": list_vpcs,
        "describe-vpc": describe_vpc,
        "list-subnets": list_subnets,
        "list-security-groups": list_security_groups,
        "get-config": get_config,
    }
    subcommand_dispatch("vpc", subcommands, args, config, session_manager)


def list_vpcs(args, config, session_manager):
    ec2 = session_manager.client("ec2")
    response = ec2.describe_vpcs()

    table = Table(title=f"VPCs ({config.region})")
    table.add_column("VPC ID", style="cyan")
    table.add_column("CIDR Block", style="green")
    table.add_column("State")
    table.add_column("Default")
    table.add_column("Name")

    for vpc in response["Vpcs"]:
        name = ""
        for tag in vpc.get("Tags", []):
            if tag["Key"] == "Name":
                name = tag["Value"]
        table.add_row(
            vpc["VpcId"],
            vpc["CidrBlock"],
            vpc["State"],
            str(vpc.get("IsDefault", False)),
            name,
        )
    console.print(table)
    console.print(f"[dim]{len(response['Vpcs'])} VPC(s) found[/dim]")


def describe_vpc(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] vpc describe-vpc <vpc-id>")
        return
    ec2 = session_manager.client("ec2")
    response = ec2.describe_vpcs(VpcIds=[args[0]])
    print_json(response["Vpcs"])


def list_subnets(args, config, session_manager):
    ec2 = session_manager.client("ec2")

    filters = []
    if args:
        filters.append({"Name": "vpc-id", "Values": [args[0]]})

    response = ec2.describe_subnets(Filters=filters) if filters else ec2.describe_subnets()

    table = Table(title=f"Subnets ({config.region})")
    table.add_column("Subnet ID", style="cyan")
    table.add_column("VPC ID")
    table.add_column("CIDR Block", style="green")
    table.add_column("AZ", style="yellow")
    table.add_column("Available IPs", justify="right")
    table.add_column("Name")

    for subnet in response["Subnets"]:
        name = ""
        for tag in subnet.get("Tags", []):
            if tag["Key"] == "Name":
                name = tag["Value"]
        table.add_row(
            subnet["SubnetId"],
            subnet["VpcId"],
            subnet["CidrBlock"],
            subnet.get("AvailabilityZone", ""),
            str(subnet.get("AvailableIpAddressCount", "")),
            name,
        )
    console.print(table)
    console.print(f"[dim]{len(response['Subnets'])} subnet(s) found[/dim]")


def list_security_groups(args, config, session_manager):
    ec2 = session_manager.client("ec2")

    filters = []
    if args:
        filters.append({"Name": "vpc-id", "Values": [args[0]]})

    response = ec2.describe_security_groups(Filters=filters) if filters else ec2.describe_security_groups()

    table = Table(title=f"Security Groups ({config.region})")
    table.add_column("Group ID", style="cyan")
    table.add_column("Group Name", style="green")
    table.add_column("VPC ID")
    table.add_column("Description")

    for sg in response["SecurityGroups"]:
        table.add_row(
            sg["GroupId"],
            sg["GroupName"],
            sg.get("VpcId", ""),
            sg.get("Description", ""),
        )
    console.print(table)
    console.print(f"[dim]{len(response['SecurityGroups'])} security group(s) found[/dim]")


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] vpc get-config <vpc-id>")
        return
    ec2 = session_manager.client("ec2")
    response = ec2.describe_vpcs(VpcIds=[args[0]])
    print_json(response["Vpcs"])
