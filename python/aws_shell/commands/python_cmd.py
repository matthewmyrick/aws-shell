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
from rich.text import Text

from ..utils.table import ResourceTable

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
    # Service clients (with helpers)
    "ec2", "s3", "iam", "lam", "cfn", "sts", "rds", "sqs", "ses",
    "opensearch", "route53", "ga_client", "cloudfront", "cw", "logs",
    "secrets", "dynamodb", "ssm_client", "ecs_client", "sso_admin",
    "elasticache", "cognito",
    # Utility functions
    "find", "client", "resource", "set_region", "set_profile",
}


class ServiceHelper:
    """Wraps a boto3 client with convenience helper methods.

    Direct client methods are available via delegation:
        ec2.describe_instances(...)  # calls boto3 client

    Helper methods provide simpler interfaces:
        ec2.list_instances()  # returns ResourceTable
    """

    def __init__(self, name, client):
        object.__setattr__(self, '_name', name)
        object.__setattr__(self, '_client', client)

    def __getattr__(self, name):
        return getattr(self._client, name)

    def __repr__(self):
        helpers = sorted(
            k for k in self.__dict__
            if not k.startswith('_') and callable(self.__dict__[k])
        )
        if helpers:
            return f"<{self._name} client — helpers: {', '.join(helpers)}>"
        return f"<{self._name} client>"

    def __dir__(self):
        own = [k for k in self.__dict__ if not k.startswith('_')]
        client_attrs = [a for a in dir(self._client) if not a.startswith('_')]
        return sorted(set(own + client_attrs))


class AWSPythonLexer(Python3Lexer):
    """Python lexer that highlights pre-loaded AWS namespace variables."""

    name = "AWSPython"

    def get_tokens_unprocessed(self, text):
        for index, tokentype, value in super().get_tokens_unprocessed(text):
            if tokentype in Name and value in _NAMESPACE_NAMES:
                yield index, Name.Builtin, value
            else:
                yield index, tokentype, value



# ResourceTable methods offered when chaining after a method call
# e.g. ec2.list_instances().filter(...)
_TABLE_METHODS = {
    "filter": ("method", "Filter rows by key=value or lambda"),
    "find": ("method", "Fuzzy search all fields"),
    "sort": ("method", "Sort by column key"),
    "select": ("method", "Choose display columns"),
    "data": ("attr", "Raw list of dicts"),
    "json": ("method", "Print as formatted JSON"),
}


class PythonCompleter(Completer):
    """Auto-completer that handles pre-loaded variables and Python attribute access."""

    def __init__(self, namespace):
        self.namespace = namespace

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor

        # Extract the current word being typed (the dotted expression at cursor)
        word = self._get_expression_at_cursor(text)

        if "." in word:
            # Attribute completion: "s3.list" -> eval("s3"), complete "list"
            dot_idx = word.rfind(".")
            obj_text = word[:dot_idx]
            partial = word[dot_idx + 1:]

            # If obj_text ends with ), it's a method call return value.
            # Don't eval (would call the API) — offer ResourceTable methods.
            if obj_text.endswith(")"):
                yield from self._complete_table_methods(partial)
                return

            try:
                obj = eval(obj_text, self.namespace)
                attrs = [a for a in dir(obj) if not a.startswith("_")]
                for attr in attrs:
                    if attr.lower().startswith(partial.lower()):
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
    def _complete_table_methods(partial):
        """Yield ResourceTable method completions for chained calls."""
        for name, (kind, desc) in _TABLE_METHODS.items():
            if name.lower().startswith(partial.lower()):
                if kind == "method":
                    yield Completion(
                        name + "()",
                        start_position=-len(partial),
                        display=name + "()",
                        display_meta=desc,
                    )
                else:
                    yield Completion(
                        name,
                        start_position=-len(partial),
                        display_meta=desc,
                    )

    @staticmethod
    def _get_expression_at_cursor(text):
        """Extract the dotted expression at the cursor position."""
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

    namespace = _build_namespace(config, session_manager)
    completer = PythonCompleter(namespace)

    console.print(
        Panel(
            "[bold]Python REPL Mode[/bold]\n\n"
            "[bold]Clients[/bold] (type name to see helpers):\n"
            "  [cyan]ec2[/cyan], [cyan]s3[/cyan], [cyan]iam[/cyan], [cyan]lam[/cyan], "
            "[cyan]cfn[/cyan], [cyan]sts[/cyan], [cyan]rds[/cyan], [cyan]sqs[/cyan], "
            "[cyan]ses[/cyan], [cyan]opensearch[/cyan],\n"
            "  [cyan]route53[/cyan], [cyan]ga_client[/cyan], [cyan]cloudfront[/cyan], "
            "[cyan]cw[/cyan], [cyan]logs[/cyan], [cyan]secrets[/cyan], [cyan]dynamodb[/cyan],\n"
            "  [cyan]ssm_client[/cyan], [cyan]ecs_client[/cyan], [cyan]sso_admin[/cyan], "
            "[cyan]elasticache[/cyan], [cyan]cognito[/cyan]\n\n"
            "[bold]Examples:[/bold]\n"
            "  [cyan]ec2.list_instances()[/cyan]                    "
            "[dim]# Rich table output[/dim]\n"
            "  [cyan]ec2.list_instances().filter(State=\"running\")[/cyan]  "
            "[dim]# Filter rows[/dim]\n"
            "  [cyan]ec2.list_instances().find(\"web\")[/cyan]           "
            "[dim]# Fuzzy search[/dim]\n"
            "  [cyan]ec2.list_instances().sort(\"Tags.Name\")[/cyan]     "
            "[dim]# Sort by column[/dim]\n"
            "  [cyan]ec2.list_instances().data[/cyan]                  "
            "[dim]# Raw list of dicts[/dim]\n"
            "  [cyan]ec2.list_instances().json()[/cyan]                "
            "[dim]# JSON output[/dim]\n"
            "  [cyan]ec2.describe_instances(InstanceIds=[...])[/cyan]  "
            "[dim]# Direct boto3 call[/dim]\n\n"
            "[bold]Utilities:[/bold]\n"
            "  [cyan]find(data, kw)[/cyan]    - Fuzzy search through any data\n"
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

        if not text.strip():
            buf.validate_and_handle()
            return

        try:
            result = compiler(text, "<input>", "exec")
        except (SyntaxError, OverflowError, ValueError):
            buf.validate_and_handle()
            return

        if result is None:
            buf.insert_text("\n")
        else:
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

    while True:
        try:
            text = py_session.prompt(">>> ")
            stripped = text.strip()
            if not stripped:
                continue
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
        result = eval(compile(code_str, "<input>", "eval"), namespace)
        if result is not None:
            if isinstance(result, ResourceTable):
                result.render()
            elif isinstance(result, (dict, list)):
                try:
                    print_json(result)
                except (TypeError, ValueError):
                    print(repr(result))
            else:
                print(repr(result))
    except SyntaxError:
        try:
            exec(compile(code_str, "<input>", "exec"), namespace)
        except Exception:
            traceback.print_exc()
    except Exception:
        traceback.print_exc()


def cmd_exec(args, config, session_manager):
    if not args:
        console.print("[yellow]Usage:[/yellow] exec <python-expression>")
        console.print("[dim]Example: exec ec2.list_instances()[/dim]")
        return

    namespace = _build_namespace(config, session_manager)
    expression = " ".join(args)

    try:
        result = eval(expression, namespace)
        if result is not None:
            if isinstance(result, ResourceTable):
                result.render()
            else:
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
        """Fuzzy search through data. For ResourceTables returns a filtered table."""
        if isinstance(data, ResourceTable):
            return data.find(keyword)

        results = fuzzy_search(data, keyword)
        if not results:
            console.print(f"[yellow]No matches for '{keyword}'[/yellow]")
            return

        console.print()
        for path, value in results:
            text = Text()
            text.append(f"  {path}", style="cyan")
            text.append(" \u2192 ", style="dim")
            display = value if len(value) <= 120 else value[:117] + "..."
            text.append(display)
            console.print(text)
        console.print(f"\n[dim]{len(results)} match(es)[/dim]")

    namespace.update({
        "__builtins__": __builtins__,
        "boto3": boto3,
        "session": session_manager._session,
        "config": config,
        # Utility functions
        "find": find,
        "client": get_client,
        "resource": get_resource,
        "set_region": set_region,
        "set_profile": set_profile,
    })

    _attach_service_helpers(namespace, session_manager)

    return namespace


# ---------------------------------------------------------------------------
# Helper factories for concise service helper creation
# ---------------------------------------------------------------------------

def _paginated_helper(sm, service, method, key, columns=None, title=None, **extra):
    """Factory: create a helper that paginates an API call and returns ResourceTable."""
    def helper():
        c = sm.client(service)
        items = []
        for page in c.get_paginator(method).paginate(**extra):
            items.extend(page.get(key, []))
        return ResourceTable(items, columns=columns, title=title)
    return helper


def _simple_helper(sm, service, method, key_path, columns=None, title=None, **call_kwargs):
    """Factory: create a helper that makes a single API call and returns ResourceTable."""
    def helper():
        c = sm.client(service)
        result = getattr(c, method)(**call_kwargs)
        data = result
        for k in key_path.split("."):
            data = data.get(k, []) if isinstance(data, dict) else data
        if not isinstance(data, list):
            data = [data] if data else []
        return ResourceTable(data, columns=columns, title=title)
    return helper


# ---------------------------------------------------------------------------
# Service helpers — each service gets a ServiceHelper with attached methods
# ---------------------------------------------------------------------------

def _attach_service_helpers(namespace, session_manager):
    """Create ServiceHelper objects with convenience methods for all services."""
    sm = session_manager

    # --- EC2 ---
    ec2 = ServiceHelper("ec2", sm.client("ec2"))

    def _ec2_list_instances():
        c = sm.client("ec2")
        instances = []
        for page in c.get_paginator("describe_instances").paginate():
            for res in page["Reservations"]:
                instances.extend(res["Instances"])
        return ResourceTable(instances, columns=[
            ("InstanceId", "Instance ID", "cyan"),
            ("Tags.Name", "Name", "green"),
            ("State.Name", "State", "bold"),
            ("InstanceType", "Type", "yellow"),
            ("PrivateIpAddress", "Private IP"),
            ("PublicIpAddress", "Public IP"),
        ], title="EC2 Instances")

    def _ec2_list_vpcs():
        return ResourceTable(
            sm.client("ec2").describe_vpcs()["Vpcs"],
            columns=[("VpcId", "VPC ID", "cyan"), ("Tags.Name", "Name", "green"),
                     ("State", "State", "bold"), ("CidrBlock", "CIDR", "yellow"),
                     ("IsDefault", "Default")],
            title="VPCs",
        )

    def _ec2_list_subnets(vpc_id=None):
        c = sm.client("ec2")
        kwargs = {"Filters": [{"Name": "vpc-id", "Values": [vpc_id]}]} if vpc_id else {}
        return ResourceTable(
            c.describe_subnets(**kwargs)["Subnets"],
            columns=[("SubnetId", "Subnet ID", "cyan"), ("Tags.Name", "Name", "green"),
                     ("VpcId", "VPC ID", "cyan"), ("CidrBlock", "CIDR", "yellow"),
                     ("AvailabilityZone", "AZ")],
            title="Subnets",
        )

    def _ec2_list_security_groups(vpc_id=None):
        c = sm.client("ec2")
        kwargs = {"Filters": [{"Name": "vpc-id", "Values": [vpc_id]}]} if vpc_id else {}
        return ResourceTable(
            c.describe_security_groups(**kwargs)["SecurityGroups"],
            columns=[("GroupId", "Group ID", "cyan"), ("GroupName", "Name", "green"),
                     ("VpcId", "VPC ID", "cyan"), ("Description", "Description")],
            title="Security Groups",
        )

    ec2.list_instances = _ec2_list_instances
    ec2.list_vpcs = _ec2_list_vpcs
    ec2.list_subnets = _ec2_list_subnets
    ec2.list_security_groups = _ec2_list_security_groups
    namespace["ec2"] = ec2

    # --- S3 ---
    s3 = ServiceHelper("s3", sm.client("s3"))

    def _s3_list_buckets():
        return ResourceTable(
            sm.client("s3").list_buckets().get("Buckets", []),
            columns=[("Name", "Bucket Name"), ("CreationDate", "Created")],
            title="S3 Buckets",
        )

    def _s3_list_bucket_names():
        buckets = sm.client("s3").list_buckets().get("Buckets", [])
        return ResourceTable(
            [b["Name"] for b in buckets],
            title="S3 Bucket Names",
        )

    s3.list_buckets = _s3_list_buckets
    s3.list_bucket_names = _s3_list_bucket_names
    namespace["s3"] = s3

    # --- IAM ---
    iam = ServiceHelper("iam", sm.client("iam"))
    iam.list_users = _paginated_helper(sm, "iam", "list_users", "Users",
        columns=[("UserName", "User"), ("UserId", "User ID"),
                 ("Arn", "ARN"), ("CreateDate", "Created")],
        title="IAM Users")
    iam.list_roles = _paginated_helper(sm, "iam", "list_roles", "Roles",
        columns=[("RoleName", "Role"), ("RoleId", "Role ID"),
                 ("Arn", "ARN"), ("CreateDate", "Created")],
        title="IAM Roles")
    iam.list_policies = _paginated_helper(sm, "iam", "list_policies", "Policies",
        columns=[("PolicyName", "Policy"), ("PolicyId", "Policy ID"),
                 ("AttachmentCount", "Attachments"), ("CreateDate", "Created")],
        title="IAM Policies", Scope="Local")
    namespace["iam"] = iam

    # --- Lambda ---
    lam = ServiceHelper("lambda", sm.client("lambda"))
    lam.list_functions = _paginated_helper(sm, "lambda", "list_functions", "Functions",
        columns=[("FunctionName", "Function"), ("Runtime", "Runtime"),
                 ("MemorySize", "Memory MB"), ("Timeout", "Timeout"),
                 ("LastModified", "Last Modified")],
        title="Lambda Functions")
    namespace["lam"] = lam

    # --- CloudFormation ---
    cfn = ServiceHelper("cfn", sm.client("cloudformation"))
    cfn.list_stacks = _paginated_helper(
        sm, "cloudformation", "list_stacks", "StackSummaries",
        columns=[("StackName", "Stack"), ("StackStatus", "Status"),
                 ("CreationTime", "Created")],
        title="CloudFormation Stacks",
        StackStatusFilter=["CREATE_COMPLETE", "UPDATE_COMPLETE", "ROLLBACK_COMPLETE"])
    namespace["cfn"] = cfn

    # --- STS (no helpers) ---
    namespace["sts"] = ServiceHelper("sts", sm.client("sts"))

    # --- RDS ---
    rds = ServiceHelper("rds", sm.client("rds"))
    rds.list_instances = _paginated_helper(
        sm, "rds", "describe_db_instances", "DBInstances",
        columns=[("DBInstanceIdentifier", "DB Instance"), ("DBInstanceClass", "Class"),
                 ("Engine", "Engine"), ("DBInstanceStatus", "Status")],
        title="RDS Instances")
    rds.list_clusters = _paginated_helper(
        sm, "rds", "describe_db_clusters", "DBClusters",
        columns=[("DBClusterIdentifier", "Cluster"), ("Engine", "Engine"),
                 ("Status", "Status"), ("Endpoint", "Endpoint")],
        title="RDS Clusters")
    namespace["rds"] = rds

    # --- SQS ---
    sqs = ServiceHelper("sqs", sm.client("sqs"))

    def _sqs_list_queues():
        return ResourceTable(
            sm.client("sqs").list_queues().get("QueueUrls", []),
            title="SQS Queues",
        )

    sqs.list_queues = _sqs_list_queues
    namespace["sqs"] = sqs

    # --- SES (no helpers) ---
    namespace["ses"] = ServiceHelper("ses", sm.client("sesv2"))

    # --- OpenSearch ---
    opensearch = ServiceHelper("opensearch", sm.client("opensearch"))
    opensearch.list_domains = _simple_helper(
        sm, "opensearch", "list_domain_names", "DomainNames",
        columns=[("DomainName", "Domain")],
        title="OpenSearch Domains")
    namespace["opensearch"] = opensearch

    # --- Route 53 ---
    route53 = ServiceHelper("route53", sm.client("route53"))
    route53.list_hosted_zones = _simple_helper(
        sm, "route53", "list_hosted_zones", "HostedZones",
        columns=[("Name", "Name"), ("Id", "Zone ID"),
                 ("ResourceRecordSetCount", "Records")],
        title="Route 53 Hosted Zones")
    namespace["route53"] = route53

    # --- Global Accelerator (no helpers) ---
    namespace["ga_client"] = ServiceHelper("ga", sm.client("globalaccelerator"))

    # --- CloudFront ---
    cloudfront = ServiceHelper("cloudfront", sm.client("cloudfront"))

    def _cf_list_distributions():
        resp = sm.client("cloudfront").list_distributions()
        items = resp.get("DistributionList", {}).get("Items", [])
        return ResourceTable(items,
            columns=[("Id", "ID"), ("DomainName", "Domain"),
                     ("Status", "Status"), ("Enabled", "Enabled")],
            title="CloudFront Distributions")

    cloudfront.list_distributions = _cf_list_distributions
    namespace["cloudfront"] = cloudfront

    # --- CloudWatch ---
    cw = ServiceHelper("cw", sm.client("cloudwatch"))
    cw.list_alarms = _paginated_helper(
        sm, "cloudwatch", "describe_alarms", "MetricAlarms",
        columns=[("AlarmName", "Alarm"), ("StateValue", "State"),
                 ("MetricName", "Metric"), ("Namespace", "Namespace")],
        title="CloudWatch Alarms")
    namespace["cw"] = cw

    # --- CloudWatch Logs ---
    logs = ServiceHelper("logs", sm.client("logs"))
    logs.list_log_groups = _paginated_helper(
        sm, "logs", "describe_log_groups", "logGroups",
        columns=[("logGroupName", "Log Group"), ("storedBytes", "Stored Bytes"),
                 ("retentionInDays", "Retention")],
        title="CloudWatch Log Groups")
    namespace["logs"] = logs

    # --- Secrets Manager ---
    secrets = ServiceHelper("secrets", sm.client("secretsmanager"))
    secrets.list_secrets = _paginated_helper(
        sm, "secretsmanager", "list_secrets", "SecretList",
        columns=[("Name", "Secret"), ("Description", "Description"),
                 ("LastChangedDate", "Last Changed")],
        title="Secrets Manager")
    namespace["secrets"] = secrets

    # --- DynamoDB ---
    dynamodb = ServiceHelper("dynamodb", sm.client("dynamodb"))

    def _ddb_list_tables():
        return ResourceTable(
            sm.client("dynamodb").list_tables().get("TableNames", []),
            title="DynamoDB Tables",
        )

    dynamodb.list_tables = _ddb_list_tables
    namespace["dynamodb"] = dynamodb

    # --- SSM ---
    ssm_client = ServiceHelper("ssm", sm.client("ssm"))
    ssm_client.list_parameters = _paginated_helper(
        sm, "ssm", "describe_parameters", "Parameters",
        columns=[("Name", "Parameter"), ("Type", "Type"),
                 ("LastModifiedDate", "Last Modified")],
        title="SSM Parameters")
    namespace["ssm_client"] = ssm_client

    # --- ECS ---
    ecs_client = ServiceHelper("ecs", sm.client("ecs"))

    def _ecs_list_clusters():
        return ResourceTable(
            sm.client("ecs").list_clusters().get("clusterArns", []),
            title="ECS Clusters",
        )

    ecs_client.list_clusters = _ecs_list_clusters
    namespace["ecs_client"] = ecs_client

    # --- SSO Admin (no helpers) ---
    namespace["sso_admin"] = ServiceHelper("sso", sm.client("sso-admin"))

    # --- ElastiCache ---
    elasticache = ServiceHelper("elasticache", sm.client("elasticache"))
    elasticache.list_clusters = _paginated_helper(
        sm, "elasticache", "describe_cache_clusters", "CacheClusters",
        columns=[("CacheClusterId", "Cluster ID"), ("CacheNodeType", "Node Type"),
                 ("Engine", "Engine"), ("CacheClusterStatus", "Status")],
        title="ElastiCache Clusters")
    namespace["elasticache"] = elasticache

    # --- Cognito ---
    cognito = ServiceHelper("cognito", sm.client("cognito-idp"))

    def _cog_list_user_pools():
        return ResourceTable(
            sm.client("cognito-idp").list_user_pools(MaxResults=60).get("UserPools", []),
            columns=[("Id", "Pool ID"), ("Name", "Name"),
                     ("Status", "Status"), ("CreationDate", "Created")],
            title="Cognito User Pools",
        )

    cognito.list_user_pools = _cog_list_user_pools
    namespace["cognito"] = cognito


def _refresh_clients(namespace, session_manager):
    """Refresh all clients and service helpers after a region/profile switch."""
    namespace["session"] = session_manager._session
    _attach_service_helpers(namespace, session_manager)
