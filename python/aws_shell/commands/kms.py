"""KMS (Key Management Service) commands."""
import base64

from rich.console import Console
from rich.table import Table
from .base import subcommand_dispatch
from ..utils.output import print_json

console = Console()


def register(registry):
    registry.register("kms", handle_kms, "KMS key management")


def handle_kms(args, config, session_manager):
    subcommands = {
        "list-keys": list_keys,
        "describe-key": describe_key,
        "list-aliases": list_aliases,
        "get-key-policy": get_key_policy,
        "get-public-key": get_public_key,
        "get-config": get_config,
    }
    subcommand_dispatch("kms", subcommands, args, config, session_manager)


def list_keys(args, config, session_manager):
    client = session_manager.client("kms")
    paginator = client.get_paginator("list_keys")

    # Also get aliases for display
    alias_map = {}
    for page in client.get_paginator("list_aliases").paginate():
        for alias in page.get("Aliases", []):
            key_id = alias.get("TargetKeyId", "")
            if key_id:
                alias_map.setdefault(key_id, []).append(alias.get("AliasName", ""))

    table = Table(title=f"KMS Keys ({config.region})")
    table.add_column("Key ID", style="cyan")
    table.add_column("Aliases", style="green")
    table.add_column("Description")
    table.add_column("State", style="bold")
    table.add_column("Key Usage", style="yellow")
    table.add_column("Origin")

    count = 0
    for page in paginator.paginate():
        for key in page.get("Keys", []):
            key_id = key["KeyId"]
            try:
                detail = client.describe_key(KeyId=key_id)["KeyMetadata"]
            except Exception:
                detail = {}
            aliases = ", ".join(alias_map.get(key_id, [])) or "-"
            table.add_row(
                key_id,
                aliases,
                detail.get("Description", ""),
                detail.get("KeyState", ""),
                detail.get("KeyUsage", ""),
                detail.get("Origin", ""),
            )
            count += 1

    console.print(table)
    console.print(f"[dim]{count} key(s) found[/dim]")


def describe_key(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] kms describe-key <key-id-or-alias>")
        console.print("[dim]Example: kms describe-key alias/my-key[/dim]")
        return
    client = session_manager.client("kms")
    response = client.describe_key(KeyId=args[0])
    response.pop("ResponseMetadata", None)
    print_json(response.get("KeyMetadata", response))


def list_aliases(args, config, session_manager):
    client = session_manager.client("kms")
    paginator = client.get_paginator("list_aliases")

    table = Table(title=f"KMS Aliases ({config.region})")
    table.add_column("Alias", style="cyan")
    table.add_column("Target Key ID", style="green")
    table.add_column("ARN")

    count = 0
    key_filter = args[0] if args else None
    for page in paginator.paginate():
        for alias in page.get("Aliases", []):
            if key_filter and key_filter not in alias.get("TargetKeyId", ""):
                continue
            table.add_row(
                alias.get("AliasName", ""),
                alias.get("TargetKeyId", ""),
                alias.get("AliasArn", ""),
            )
            count += 1

    console.print(table)
    console.print(f"[dim]{count} alias(es) found[/dim]")


def get_key_policy(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] kms get-key-policy <key-id-or-alias>")
        return
    client = session_manager.client("kms")
    import json
    response = client.get_key_policy(KeyId=args[0], PolicyName="default")
    policy_str = response.get("Policy", "{}")
    try:
        print_json(json.loads(policy_str))
    except (json.JSONDecodeError, TypeError):
        console.print(policy_str)


def get_public_key(args, config, session_manager):
    """Download the public key for an asymmetric KMS key."""
    if not args:
        console.print("[yellow]Usage:[/yellow] kms get-public-key <key-id-or-alias> [output-file]")
        console.print("[dim]Saves PEM-encoded public key. Only works for asymmetric keys.[/dim]")
        return
    client = session_manager.client("kms")
    try:
        response = client.get_public_key(KeyId=args[0])
    except client.exceptions.UnsupportedOperationException:
        console.print("[bold red]Error:[/bold red] This key is not asymmetric — only asymmetric keys have downloadable public keys.")
        return

    pub_key_der = response["PublicKey"]
    pem_body = base64.b64encode(pub_key_der).decode("ascii")
    # Format as PEM
    pem_lines = [pem_body[i:i+64] for i in range(0, len(pem_body), 64)]
    pem = "-----BEGIN PUBLIC KEY-----\n" + "\n".join(pem_lines) + "\n-----END PUBLIC KEY-----\n"

    if len(args) > 1:
        output_file = args[1]
        with open(output_file, "w") as f:
            f.write(pem)
        console.print(f"[green]Public key saved to:[/green] {output_file}")
    else:
        console.print(pem)

    console.print(f"[dim]Algorithm: {response.get('KeyUsage', '')} / {response.get('CustomerMasterKeySpec', response.get('KeySpec', ''))}[/dim]")


def get_config(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] kms get-config <key-id-or-alias>")
        return
    client = session_manager.client("kms")
    result = {}
    try:
        result["KeyMetadata"] = client.describe_key(KeyId=args[0]).get("KeyMetadata", {})
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        return
    try:
        import json
        policy = client.get_key_policy(KeyId=args[0], PolicyName="default").get("Policy", "{}")
        result["KeyPolicy"] = json.loads(policy)
    except Exception:
        pass
    try:
        result["Aliases"] = client.list_aliases(KeyId=args[0]).get("Aliases", [])
    except Exception:
        pass
    try:
        result["Grants"] = client.list_grants(KeyId=args[0]).get("Grants", [])
    except Exception:
        pass
    print_json(result)
