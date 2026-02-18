"""Python REPL mode - run arbitrary Python with boto3 pre-loaded."""
import codeop
import os
import traceback

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.styles import Style
from pygments.lexers.python import Python3Lexer
from pygments.token import Name
from rich.console import Console
from rich.panel import Panel

console = Console()

PYTHON_STYLE = Style.from_dict({
    "prompt": "bold #a6e22e",
    "continuation": "bold #666666",
    "bottom-toolbar": "bg:#232f3e #ffffff",
    "completion-menu.completion": "bg:#232f3e #ffffff",
    "completion-menu.completion.current": "bg:#a6e22e #000000",
})


# Pre-loaded namespace variable names for syntax highlighting
_NAMESPACE_NAMES = {
    "session", "boto3", "config",
    # Raw clients
    "ec2", "s3", "iam", "lam", "cfn", "sts", "rds", "sqs", "ses",
    "opensearch", "route53", "ga_client", "cloudfront", "cw", "logs",
    "secrets", "dynamodb", "ssm_client", "ecs_client", "sso_admin",
    "elasticache", "cognito",
    # Utility functions
    "find", "client", "resource", "set_region", "set_profile",
    # Helper functions
    "list_instances", "list_vpcs", "list_subnets", "list_security_groups",
    "list_buckets", "list_bucket_names", "list_functions",
    "list_users", "list_roles", "list_policies", "list_stacks",
    "list_queues", "list_db_instances", "list_db_clusters",
    "list_domains", "list_hosted_zones", "list_distributions",
    "list_alarms", "list_log_groups", "list_secrets",
    "list_tables", "list_parameters", "list_clusters",
    "list_cache_clusters", "list_user_pools",
}


class AWSPythonLexer(Python3Lexer):
    """Python lexer that highlights pre-loaded AWS namespace variables."""

    name = "AWSPython"

    def get_tokens_unprocessed(self, text):
        for index, tokentype, value in super().get_tokens_unprocessed(text):
            if tokentype in Name and value in _NAMESPACE_NAMES:
                yield index, Name.Builtin, value
            else:
                yield index, tokentype, value


class PythonCompleter(Completer):
    """Auto-completer that handles pre-loaded variables and Python attribute access."""

    def __init__(self, namespace):
        self.namespace = namespace

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor

        # Extract the current word being typed (the dotted expression at cursor)
        # Walk backwards from cursor to find the start of the expression
        word = self._get_expression_at_cursor(text)

        if "." in word:
            # Attribute completion: "s3.list" -> eval("s3"), complete "list"
            dot_idx = word.rfind(".")
            obj_text = word[:dot_idx]
            partial = word[dot_idx + 1:]

            try:
                obj = eval(obj_text, self.namespace)
                attrs = [a for a in dir(obj) if not a.startswith("_")]
                for attr in attrs:
                    if attr.lower().startswith(partial.lower()):
                        # Add () suffix for callable attributes (methods/functions)
                        member = getattr(obj, attr, None)
                        if callable(member):
                            yield Completion(
                                attr + "()",
                                start_position=-len(partial),
                                display=attr + "()",
                                display_meta="method",
                            )
                        else:
                            yield Completion(
                                attr,
                                start_position=-len(partial),
                                display_meta="attr",
                            )
            except Exception:
                return
        else:
            # Complete from namespace keys + Python builtins
            partial = word
            candidates = list(self.namespace.keys())
            candidates += ["True", "False", "None", "print", "len", "type",
                           "list", "dict", "str", "int", "float", "bool",
                           "range", "enumerate", "zip", "map", "filter",
                           "sorted", "reversed", "isinstance", "hasattr",
                           "getattr", "setattr", "import", "from", "for",
                           "while", "if", "else", "elif", "try", "except",
                           "with", "as", "def", "class", "return", "yield",
                           "lambda", "and", "or", "not", "in", "is"]
            for name in candidates:
                if name.startswith("__"):
                    continue
                if name.lower().startswith(partial.lower()):
                    # Check if it's callable in the namespace
                    ns_val = self.namespace.get(name)
                    if ns_val is not None and callable(ns_val):
                        yield Completion(
                            name + "()",
                            start_position=-len(partial),
                            display=name + "()",
                            display_meta="func",
                        )
                    else:
                        yield Completion(name, start_position=-len(partial))

    @staticmethod
    def _get_expression_at_cursor(text):
        """Extract the dotted expression at the cursor position.

        For 'for x in s3.list' returns 's3.list'
        For 'result = boto3.cl' returns 'boto3.cl'
        For 'pri' returns 'pri'
        """
        # Walk backwards from end to find the start of the identifier/dotted expression
        i = len(text) - 1
        while i >= 0 and (text[i].isalnum() or text[i] in ("_", ".")):
            i -= 1
        return text[i + 1:]


def register(registry):
    registry.register("py", cmd_python, "Enter Python REPL with boto3 pre-loaded")
    registry.register("python", cmd_python, "Enter Python REPL with boto3 pre-loaded")
    registry.register("exec", cmd_exec, "Execute a single Python expression")


def cmd_python(args, config, session_manager):
    # If args were passed, execute as a one-liner
    if args:
        cmd_exec(args, config, session_manager)
        return

    # Build the namespace with useful pre-loaded objects
    namespace = _build_namespace(config, session_manager)
    completer = PythonCompleter(namespace)

    console.print(
        Panel(
            "[bold]Python REPL Mode[/bold]\n\n"
            "[bold]Clients:[/bold] ec2, s3, iam, lam, cfn, sts, rds, sqs, ses, opensearch,\n"
            "  route53, ga_client, cloudfront, cw, logs, secrets, dynamodb,\n"
            "  ssm_client, ecs_client, sso_admin, elasticache, cognito\n\n"
            "[bold]Helpers[/bold] (return raw data):\n"
            "  [cyan]list_instances()[/cyan]        [cyan]list_vpcs()[/cyan]           [cyan]list_subnets()[/cyan]\n"
            "  [cyan]list_security_groups()[/cyan]  [cyan]list_buckets()[/cyan]        [cyan]list_bucket_names()[/cyan]\n"
            "  [cyan]list_functions()[/cyan]        [cyan]list_users()[/cyan]          [cyan]list_roles()[/cyan]\n"
            "  [cyan]list_policies()[/cyan]         [cyan]list_stacks()[/cyan]         [cyan]list_queues()[/cyan]\n"
            "  [cyan]list_db_instances()[/cyan]     [cyan]list_db_clusters()[/cyan]    [cyan]list_domains()[/cyan]\n"
            "  [cyan]list_hosted_zones()[/cyan]     [cyan]list_distributions()[/cyan]  [cyan]list_alarms()[/cyan]\n"
            "  [cyan]list_log_groups()[/cyan]       [cyan]list_secrets()[/cyan]        [cyan]list_tables()[/cyan]\n"
            "  [cyan]list_parameters()[/cyan]       [cyan]list_clusters()[/cyan]       [cyan]list_cache_clusters()[/cyan]\n"
            "  [cyan]list_user_pools()[/cyan]\n\n"
            "[bold]Utilities:[/bold]\n"
            "  [cyan]find(data, kw)[/cyan]    - Fuzzy search through JSON data\n"
            "  [cyan]client(name)[/cyan]      - Get any boto3 client\n"
            "  [cyan]resource(name)[/cyan]    - Get any boto3 resource\n"
            "  [cyan]set_region(name)[/cyan]  - Switch region (refreshes all clients)\n"
            "  [cyan]set_profile(name)[/cyan] - Switch profile (refreshes all clients)\n\n"
            "Type [bold]exit[/bold] or [bold]Ctrl+D[/bold] to return to AWS Shell.",
            title="Python Mode",
            border_style="green",
        )
    )

    history_path = os.path.expanduser("~/.aws_shell_python_history")
    compiler = codeop.CommandCompiler()

    # Key bindings: Enter auto-submits if code is complete, otherwise adds a newline
    bindings = KeyBindings()

    @bindings.add(Keys.Enter)
    def _handle_enter(event):
        buf = event.current_buffer
        text = buf.text

        # Empty input -> submit (becomes a no-op in the loop)
        if not text.strip():
            buf.validate_and_handle()
            return

        # Try to compile — if None, code is incomplete, add a newline
        try:
            result = compiler(text, "<input>", "exec")
        except (SyntaxError, OverflowError, ValueError):
            # Syntax error — submit so the user sees the error
            buf.validate_and_handle()
            return

        if result is None:
            # Incomplete (e.g., open block, unterminated string) — add newline
            buf.insert_text("\n")
        else:
            # Complete statement — submit
            buf.validate_and_handle()

    py_session = PromptSession(
        history=FileHistory(history_path),
        lexer=PygmentsLexer(AWSPythonLexer),
        completer=completer,
        style=PYTHON_STYLE,
        auto_suggest=AutoSuggestFromHistory(),
        complete_while_typing=True,
        multiline=True,
        key_bindings=bindings,
        prompt_continuation="... ",
    )

    # The REPL loop
    while True:
        try:
            text = py_session.prompt(">>> ")

            stripped = text.strip()
            if not stripped:
                continue

            # Handle exit commands
            if stripped in ("exit", "exit()", "quit", "quit()"):
                console.print("[dim]Returning to AWS Shell...[/dim]")
                break

            _exec_python(text, namespace)

        except KeyboardInterrupt:
            console.print("\nKeyboardInterrupt")
            continue
        except EOFError:
            console.print("[dim]\nReturning to AWS Shell...[/dim]")
            break


def _exec_python(code_str, namespace):
    """Execute Python code - try eval first (for expressions), fall back to exec."""
    from ..utils.output import print_json

    try:
        # Try as an expression first (returns a value)
        result = eval(compile(code_str, "<input>", "eval"), namespace)
        if result is not None:
            # Pretty-print dicts/lists as JSON, fall back to repr for other types
            if isinstance(result, (dict, list)):
                try:
                    print_json(result)
                except (TypeError, ValueError):
                    print(repr(result))
            else:
                print(repr(result))
    except SyntaxError:
        # Not an expression, execute as statement(s)
        try:
            exec(compile(code_str, "<input>", "exec"), namespace)
        except Exception:
            traceback.print_exc()
    except Exception:
        traceback.print_exc()


def cmd_exec(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] exec <python-expression>")
        console.print("[dim]Example: exec boto3.client('s3').list_buckets()['Buckets'][/dim]")
        return

    namespace = _build_namespace(config, session_manager)
    expression = " ".join(args)

    try:
        result = eval(expression, namespace)
        if result is not None:
            from ..utils.output import print_json
            try:
                print_json(result)
            except (TypeError, ValueError):
                console.print(repr(result))
    except SyntaxError:
        try:
            exec(expression, namespace)
        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")


def _build_namespace(config, session_manager):
    import boto3
    from ..utils.search import fuzzy_search

    namespace = {}

    def get_client(service_name):
        return session_manager.client(service_name)

    def get_resource(service_name):
        return session_manager._session.resource(service_name, region_name=config.region)

    def set_region(region):
        """Switch AWS region. Rebuilds session and refreshes all clients."""
        session_manager.switch_region(region)
        _refresh_clients(namespace, session_manager)
        print(f"Region set to: {region}")

    def set_profile(profile):
        """Switch AWS profile. Rebuilds session and refreshes all clients."""
        session_manager.switch_profile(profile)
        _refresh_clients(namespace, session_manager)
        print(f"Profile set to: {profile}")

    def find(data, keyword):
        """Fuzzy search through JSON data. Returns matching key paths and values."""
        results = fuzzy_search(data, keyword)
        if not results:
            print(f"No matches for '{keyword}'")
            return []
        for path, value in results:
            display = value if len(value) <= 100 else value[:97] + "..."
            print(f"  {path}: {display}")
        print(f"\n{len(results)} match(es)")
        return results

    # --- Helper functions that mirror shell commands but return raw data ---

    def list_instances():
        """List all EC2 instances. Returns list of instance dicts."""
        c = session_manager.client("ec2")
        instances = []
        for page in c.get_paginator("describe_instances").paginate():
            for res in page["Reservations"]:
                instances.extend(res["Instances"])
        return instances

    def list_vpcs():
        """List all VPCs. Returns list of VPC dicts."""
        return session_manager.client("ec2").describe_vpcs()["Vpcs"]

    def list_subnets(vpc_id=None):
        """List subnets, optionally filtered by VPC ID."""
        c = session_manager.client("ec2")
        kwargs = {"Filters": [{"Name": "vpc-id", "Values": [vpc_id]}]} if vpc_id else {}
        return c.describe_subnets(**kwargs)["Subnets"]

    def list_security_groups(vpc_id=None):
        """List security groups, optionally filtered by VPC ID."""
        c = session_manager.client("ec2")
        kwargs = {"Filters": [{"Name": "vpc-id", "Values": [vpc_id]}]} if vpc_id else {}
        return c.describe_security_groups(**kwargs)["SecurityGroups"]

    def list_buckets():
        """List all S3 buckets. Returns list of bucket dicts."""
        return session_manager.client("s3").list_buckets().get("Buckets", [])

    def list_bucket_names():
        """List just S3 bucket names. Returns list of strings."""
        return [b["Name"] for b in list_buckets()]

    def list_functions():
        """List all Lambda functions. Returns list of function dicts."""
        c = session_manager.client("lambda")
        funcs = []
        for page in c.get_paginator("list_functions").paginate():
            funcs.extend(page["Functions"])
        return funcs

    def list_users():
        """List all IAM users. Returns list of user dicts."""
        c = session_manager.client("iam")
        users = []
        for page in c.get_paginator("list_users").paginate():
            users.extend(page["Users"])
        return users

    def list_roles():
        """List all IAM roles. Returns list of role dicts."""
        c = session_manager.client("iam")
        roles = []
        for page in c.get_paginator("list_roles").paginate():
            roles.extend(page["Roles"])
        return roles

    def list_policies():
        """List customer-managed IAM policies. Returns list of policy dicts."""
        c = session_manager.client("iam")
        policies = []
        for page in c.get_paginator("list_policies").paginate(Scope="Local"):
            policies.extend(page["Policies"])
        return policies

    def list_stacks():
        """List active CloudFormation stacks. Returns list of stack dicts."""
        c = session_manager.client("cloudformation")
        stacks = []
        for page in c.get_paginator("list_stacks").paginate(
            StackStatusFilter=["CREATE_COMPLETE", "UPDATE_COMPLETE", "ROLLBACK_COMPLETE"]
        ):
            stacks.extend(page.get("StackSummaries", []))
        return stacks

    def list_queues():
        """List all SQS queue URLs. Returns list of URL strings."""
        return session_manager.client("sqs").list_queues().get("QueueUrls", [])

    def list_db_instances():
        """List all RDS instances. Returns list of DB instance dicts."""
        c = session_manager.client("rds")
        instances = []
        for page in c.get_paginator("describe_db_instances").paginate():
            instances.extend(page["DBInstances"])
        return instances

    def list_db_clusters():
        """List all RDS/Aurora clusters. Returns list of cluster dicts."""
        c = session_manager.client("rds")
        clusters = []
        for page in c.get_paginator("describe_db_clusters").paginate():
            clusters.extend(page["DBClusters"])
        return clusters

    def list_domains():
        """List OpenSearch domain names. Returns list of domain dicts."""
        return session_manager.client("opensearch").list_domain_names().get("DomainNames", [])

    def list_hosted_zones():
        """List Route 53 hosted zones. Returns list of zone dicts."""
        return session_manager.client("route53").list_hosted_zones().get("HostedZones", [])

    def list_distributions():
        """List CloudFront distributions. Returns list of distribution dicts."""
        resp = session_manager.client("cloudfront").list_distributions()
        return resp.get("DistributionList", {}).get("Items", [])

    def list_alarms():
        """List CloudWatch alarms. Returns list of alarm dicts."""
        c = session_manager.client("cloudwatch")
        alarms = []
        for page in c.get_paginator("describe_alarms").paginate():
            alarms.extend(page.get("MetricAlarms", []))
        return alarms

    def list_log_groups():
        """List CloudWatch log groups. Returns list of log group dicts."""
        c = session_manager.client("logs")
        groups = []
        for page in c.get_paginator("describe_log_groups").paginate():
            groups.extend(page.get("logGroups", []))
        return groups

    def list_secrets():
        """List Secrets Manager secrets (metadata only). Returns list of secret dicts."""
        c = session_manager.client("secretsmanager")
        secs = []
        for page in c.get_paginator("list_secrets").paginate():
            secs.extend(page.get("SecretList", []))
        return secs

    def list_tables():
        """List DynamoDB table names. Returns list of name strings."""
        return session_manager.client("dynamodb").list_tables().get("TableNames", [])

    def list_parameters():
        """List SSM parameters. Returns list of parameter dicts."""
        c = session_manager.client("ssm")
        params = []
        for page in c.get_paginator("describe_parameters").paginate():
            params.extend(page.get("Parameters", []))
        return params

    def list_clusters():
        """List ECS cluster ARNs. Returns list of ARN strings."""
        return session_manager.client("ecs").list_clusters().get("clusterArns", [])

    def list_cache_clusters():
        """List ElastiCache clusters. Returns list of cluster dicts."""
        c = session_manager.client("elasticache")
        clusters = []
        for page in c.get_paginator("describe_cache_clusters").paginate():
            clusters.extend(page.get("CacheClusters", []))
        return clusters

    def list_user_pools():
        """List Cognito user pools. Returns list of pool dicts."""
        return session_manager.client("cognito-idp").list_user_pools(MaxResults=60).get("UserPools", [])

    namespace.update({
        "__builtins__": __builtins__,
        "boto3": boto3,
        "session": session_manager._session,
        "config": config,
        # Raw clients
        "ec2": session_manager.client("ec2"),
        "s3": session_manager.client("s3"),
        "iam": session_manager.client("iam"),
        "lam": session_manager.client("lambda"),
        "cfn": session_manager.client("cloudformation"),
        "sts": session_manager.client("sts"),
        "rds": session_manager.client("rds"),
        "sqs": session_manager.client("sqs"),
        "ses": session_manager.client("sesv2"),
        "opensearch": session_manager.client("opensearch"),
        "route53": session_manager.client("route53"),
        "ga_client": session_manager.client("globalaccelerator"),
        "cloudfront": session_manager.client("cloudfront"),
        "cw": session_manager.client("cloudwatch"),
        "logs": session_manager.client("logs"),
        "secrets": session_manager.client("secretsmanager"),
        "dynamodb": session_manager.client("dynamodb"),
        "ssm_client": session_manager.client("ssm"),
        "ecs_client": session_manager.client("ecs"),
        "sso_admin": session_manager.client("sso-admin"),
        "elasticache": session_manager.client("elasticache"),
        "cognito": session_manager.client("cognito-idp"),
        # Utility functions
        "find": find,
        "client": get_client,
        "resource": get_resource,
        "set_region": set_region,
        "set_profile": set_profile,
        # Helper functions (return raw data)
        "list_instances": list_instances,
        "list_vpcs": list_vpcs,
        "list_subnets": list_subnets,
        "list_security_groups": list_security_groups,
        "list_buckets": list_buckets,
        "list_bucket_names": list_bucket_names,
        "list_functions": list_functions,
        "list_users": list_users,
        "list_roles": list_roles,
        "list_policies": list_policies,
        "list_stacks": list_stacks,
        "list_queues": list_queues,
        "list_db_instances": list_db_instances,
        "list_db_clusters": list_db_clusters,
        "list_domains": list_domains,
        "list_hosted_zones": list_hosted_zones,
        "list_distributions": list_distributions,
        "list_alarms": list_alarms,
        "list_log_groups": list_log_groups,
        "list_secrets": list_secrets,
        "list_tables": list_tables,
        "list_parameters": list_parameters,
        "list_clusters": list_clusters,
        "list_cache_clusters": list_cache_clusters,
        "list_user_pools": list_user_pools,
    })

    return namespace


def _refresh_clients(namespace, session_manager):
    """Refresh pre-loaded clients after a region/profile switch."""
    namespace["session"] = session_manager._session
    namespace["ec2"] = session_manager.client("ec2")
    namespace["s3"] = session_manager.client("s3")
    namespace["iam"] = session_manager.client("iam")
    namespace["lam"] = session_manager.client("lambda")
    namespace["cfn"] = session_manager.client("cloudformation")
    namespace["sts"] = session_manager.client("sts")
    namespace["rds"] = session_manager.client("rds")
    namespace["sqs"] = session_manager.client("sqs")
    namespace["ses"] = session_manager.client("sesv2")
    namespace["opensearch"] = session_manager.client("opensearch")
    namespace["route53"] = session_manager.client("route53")
    namespace["ga_client"] = session_manager.client("globalaccelerator")
    namespace["cloudfront"] = session_manager.client("cloudfront")
    namespace["cw"] = session_manager.client("cloudwatch")
    namespace["logs"] = session_manager.client("logs")
    namespace["secrets"] = session_manager.client("secretsmanager")
    namespace["dynamodb"] = session_manager.client("dynamodb")
    namespace["ssm_client"] = session_manager.client("ssm")
    namespace["ecs_client"] = session_manager.client("ecs")
    namespace["sso_admin"] = session_manager.client("sso-admin")
    namespace["elasticache"] = session_manager.client("elasticache")
    namespace["cognito"] = session_manager.client("cognito-idp")
