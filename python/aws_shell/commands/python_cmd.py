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
    "ec2", "vpc", "asg", "s3", "iam", "lam", "cfn", "sts", "rds", "sqs", "ses",
    "opensearch", "route53", "ga_client", "cloudfront", "cw", "logs",
    "secrets", "dynamodb", "ssm_client", "ecs_client", "sso_admin",
    "cache", "cognito",
    # Utility functions
    "find", "docs", "raw", "client", "resource", "set_region", "set_profile",
    "ai",
}


def _auto_table(response):
    """Convert a boto3 response dict into a ResourceTable when possible.

    Strips ResponseMetadata and looks for the largest list of dicts in the
    response.  If found, wraps it in a ResourceTable for automatic table
    rendering.  Otherwise returns the cleaned dict as-is.
    """
    if not isinstance(response, dict):
        return response

    # Strip metadata
    cleaned = {k: v for k, v in response.items() if k != "ResponseMetadata"}

    # Find the best list of dicts in the response
    best_key = None
    best_list = None
    for key, value in cleaned.items():
        if isinstance(value, list) and value and isinstance(value[0], dict):
            if best_list is None or len(value) > len(best_list):
                best_key = key
                best_list = value
        # Handle nested: e.g. DistributionList -> Items
        elif isinstance(value, dict):
            for subkey, subval in value.items():
                if isinstance(subval, list) and subval and isinstance(subval[0], dict):
                    if best_list is None or len(subval) > len(best_list):
                        best_key = f"{key}.{subkey}"
                        best_list = subval

    if best_list is not None:
        return ResourceTable(best_list, title=best_key)

    # If there's a simple list of strings/numbers (like QueueUrls, clusterArns)
    for key, value in cleaned.items():
        if isinstance(value, list) and value and not isinstance(value[0], dict):
            return ResourceTable(value, title=key)

    # Single-item responses: return the cleaned dict directly
    if len(cleaned) == 1:
        return list(cleaned.values())[0]

    return cleaned


class ServiceHelper:
    """Wraps a boto3 client with convenience helper methods.

    Direct client methods are available via delegation:
        ec2.describe_instances(...)  # calls boto3 client → auto-table

    Helper methods provide simpler interfaces:
        ec2.list_instances()  # returns ResourceTable
    """

    def __init__(self, name, client):
        object.__setattr__(self, '_name', name)
        object.__setattr__(self, '_client', client)

    def __getattr__(self, name):
        attr = getattr(self._client, name)
        if not callable(attr):
            return attr

        def wrapper(*args, **kwargs):
            result = attr(*args, **kwargs)
            return _auto_table(result)

        wrapper.__name__ = name
        wrapper.__doc__ = getattr(attr, '__doc__', None)
        return wrapper

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
    "help": ("method", "Show all table methods"),
    "docs": ("attr", "Show docs for this method"),
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

            # Detect chained method calls: something().partial
            # _get_expression_at_cursor stops at ), so check if the char
            # just before our extracted word is ) or obj_text ends with )
            preceding_idx = len(text) - len(word) - 1
            is_chained = (
                obj_text.endswith(")")
                or (preceding_idx >= 0 and text[preceding_idx] == ")")
            )
            if is_chained:
                yield from self._complete_table_methods(partial)
                return

            try:
                obj = eval(obj_text, self.namespace)
                attrs = [a for a in dir(obj) if not a.startswith("_")]
                partial_lower = partial.lower()

                # Split into prefix matches (shown first) and contains matches
                prefix_matches = []
                contains_matches = []
                for attr in attrs:
                    attr_lower = attr.lower()
                    if attr_lower.startswith(partial_lower):
                        prefix_matches.append(attr)
                    elif partial_lower in attr_lower:
                        contains_matches.append(attr)

                for attr in prefix_matches + contains_matches:
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
            partial_lower = partial.lower()
            candidates = list(self.namespace.keys())
            candidates += ["True", "False", "None", "print", "len", "type",
                           "list", "dict", "str", "int", "float", "bool",
                           "range", "enumerate", "zip", "map", "filter",
                           "sorted", "reversed", "isinstance", "hasattr",
                           "getattr", "setattr", "import", "from", "for",
                           "while", "if", "else", "elif", "try", "except",
                           "with", "as", "def", "class", "return", "yield",
                           "lambda", "and", "or", "not", "in", "is"]

            # Split into prefix matches (shown first) and contains matches
            prefix_matches = []
            contains_matches = []
            for name in candidates:
                if name.startswith("__"):
                    continue
                name_lower = name.lower()
                if name_lower.startswith(partial_lower):
                    prefix_matches.append(name)
                elif partial_lower in name_lower:
                    contains_matches.append(name)

            for name in prefix_matches + contains_matches:
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
            "  [cyan]ec2[/cyan], [cyan]vpc[/cyan], [cyan]asg[/cyan], [cyan]s3[/cyan], "
            "[cyan]iam[/cyan], [cyan]lam[/cyan], [cyan]cfn[/cyan], [cyan]sts[/cyan], "
            "[cyan]rds[/cyan], [cyan]sqs[/cyan], [cyan]ses[/cyan], [cyan]opensearch[/cyan],\n"
            "  [cyan]route53[/cyan], [cyan]ga_client[/cyan], [cyan]cloudfront[/cyan], "
            "[cyan]cw[/cyan], [cyan]logs[/cyan], [cyan]secrets[/cyan], [cyan]dynamodb[/cyan],\n"
            "  [cyan]ssm_client[/cyan], [cyan]ecs_client[/cyan], [cyan]sso_admin[/cyan], "
            "[cyan]cache[/cyan], [cyan]cognito[/cyan]\n\n"
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
            "  [cyan]docs()[/cyan]            - Overview of all clients & helpers\n"
            "  [cyan]docs(ec2)[/cyan]         - Show helpers for a client\n"
            "  [cyan]docs(find)[/cyan]        - Show docs for any function\n"
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
    # Inside indented blocks, Enter always adds a newline; submit with a blank line.
    # Ctrl+R: reverse history search
    bindings = KeyBindings()

    @bindings.add(Keys.Enter)
    def _handle_enter(event):
        buf = event.current_buffer
        text = buf.text

        if not text.strip():
            buf.validate_and_handle()
            return

        # If the last line is indented, we're inside a block — always add newline
        last_line = text.split("\n")[-1]
        if last_line and last_line[0] in (" ", "\t"):
            buf.insert_text("\n")
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

    @bindings.add(Keys.ControlR)
    def _reverse_search(event):
        from prompt_toolkit.search import start_search, SearchDirection
        start_search(direction=SearchDirection.BACKWARD)

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
            text = _rewrite_shell_style(text)
            _exec_python(text, namespace)
        except KeyboardInterrupt:
            console.print("\nKeyboardInterrupt")
            continue
        except EOFError:
            console.print("[dim]\nReturning to AWS Shell...[/dim]")
            break


def _rewrite_shell_style(text):
    """Rewrite shell-style commands to valid Python calls.

    Converts e.g. ``ai how do I list EC2s`` to ``ai("how do I list EC2s")``.
    Only triggers when the line starts with a known function name followed by
    bare words (no parentheses).
    """
    import re
    stripped = text.strip()
    # Match: ai <anything that doesn't start with ( >
    m = re.match(r'^ai\s+(?!\()(.*)', stripped)
    if m:
        arg = m.group(1)
        # Strip surrounding quotes if the user already wrapped them
        if (arg.startswith('"') and arg.endswith('"')) or (arg.startswith("'") and arg.endswith("'")):
            return f'ai({arg})'
        # Escape any embedded quotes
        escaped = arg.replace('\\', '\\\\').replace('"', '\\"')
        return f'ai("{escaped}")'
    return text


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

    def docs(obj=None):
        """Show documentation for a client, function, or method."""
        from rich.panel import Panel
        from rich.table import Table as RichTable

        if obj is None:
            # General overview
            clients = []
            for key, val in sorted(namespace.items()):
                if isinstance(val, ServiceHelper):
                    helpers = sorted(
                        k for k in val.__dict__
                        if not k.startswith('_') and callable(val.__dict__[k])
                    )
                    helpers_str = ", ".join(f"[cyan].{h}()[/cyan]" for h in helpers) if helpers else "[dim]no helpers[/dim]"
                    clients.append((f"[bold]{key}[/bold]", helpers_str))

            table = RichTable(title="Available Clients & Helpers", show_lines=True)
            table.add_column("Client", style="green", min_width=12)
            table.add_column("Helper Methods")
            for name, helpers in clients:
                table.add_row(name, helpers)
            console.print(table)

            console.print(Panel(
                "[bold]Utilities:[/bold]\n"
                "  [cyan]find(data, kw)[/cyan]    Fuzzy search through any data\n"
                "  [cyan]docs()[/cyan]            Show this overview\n"
                "  [cyan]docs(ec2)[/cyan]         Show helpers for a client\n"
                "  [cyan]docs(find)[/cyan]        Show docs for a function\n"
                "  [cyan]client(name)[/cyan]      Get any boto3 client\n"
                "  [cyan]resource(name)[/cyan]    Get any boto3 resource\n"
                "  [cyan]set_region(name)[/cyan]  Switch region\n"
                "  [cyan]set_profile(name)[/cyan] Switch profile\n\n"
                "[bold]Table Methods[/bold] (call [cyan].help()[/cyan] on any table):\n"
                "  [cyan].filter()[/cyan] [cyan].find()[/cyan] [cyan].sort()[/cyan] "
                "[cyan].select()[/cyan] [cyan].data[/cyan] [cyan].json()[/cyan] [cyan].help()[/cyan]",
                title="Quick Reference",
                border_style="green",
            ))
            return

        if isinstance(obj, ServiceHelper):
            # Show client helpers
            helpers = sorted(
                k for k in obj.__dict__
                if not k.startswith('_') and callable(obj.__dict__[k])
            )
            lines = [f"[bold]{obj._name}[/bold] client\n"]
            if helpers:
                lines.append("[bold]Helper methods:[/bold]")
                for h in helpers:
                    func = obj.__dict__[h]
                    doc = (func.__doc__ or "").strip().split("\n")[0]
                    lines.append(f"  [cyan]{obj._name}.{h}()[/cyan]  {doc}")
            lines.append(f"\n[bold]Direct boto3 methods:[/bold]")
            lines.append(f"  [dim]All {obj._name}.* boto3 methods work too, e.g.:[/dim]")
            client_methods = [a for a in dir(obj._client) if not a.startswith('_') and callable(getattr(obj._client, a, None))]
            sample = client_methods[:8]
            lines.append(f"  [dim]{', '.join(sample)}{'...' if len(client_methods) > 8 else ''}[/dim]")
            console.print(Panel("\n".join(lines), title=f"docs({obj._name})", border_style="cyan"))
            return

        if isinstance(obj, ResourceTable):
            obj.help()
            return

        if callable(obj):
            import inspect
            name = getattr(obj, '__name__', str(obj))
            doc = inspect.getdoc(obj) or "No documentation available."
            try:
                sig = str(inspect.signature(obj))
            except (ValueError, TypeError):
                sig = "(...)"
            console.print(Panel(
                f"[bold cyan]{name}[/bold cyan][dim]{sig}[/dim]\n\n{doc}",
                title=f"docs({name})",
                border_style="cyan",
            ))
            return

        console.print(f"[yellow]No docs for {type(obj).__name__}: {obj!r}[/yellow]")

    import builtins as _builtins
    _original_print = _builtins.print

    def smart_print(*args, **kwargs):
        """Print with auto-prettified JSON for dicts and lists."""
        from ..utils.output import print_json
        if len(args) == 1 and not kwargs.get("file") and isinstance(args[0], (dict, list)):
            try:
                print_json(args[0])
            except (TypeError, ValueError):
                _original_print(*args, **kwargs)
        else:
            _original_print(*args, **kwargs)

    def raw(*args):
        """Print raw unformatted repr of any object."""
        for arg in args:
            _original_print(repr(arg))

    def ai(question):
        """Ask the AI assistant a question about AWS.

        Examples:
            ai("how do I list running EC2 instances?")
            ai("what permissions does my role have?")
            ai("clear")  — clear conversation history
        """
        from .ai_cmd import cmd_ai
        if isinstance(question, str):
            args = question.split() if question.strip() else []
        else:
            args = [str(question)]
        # In REPL mode, no registry — suggested commands are printed but not auto-executed
        cmd_ai(args, config, session_manager, registry=None)

    namespace.update({
        "__builtins__": __builtins__,
        "boto3": boto3,
        "session": session_manager._session,
        "config": config,
        # Utility functions
        "print": smart_print,
        "raw": raw,
        "find": find,
        "docs": docs,
        "client": get_client,
        "resource": get_resource,
        "set_region": set_region,
        "set_profile": set_profile,
        "ai": ai,
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


def _format_sg_rules(rules):
    """Format security group rules into a readable multi-line string."""
    lines = []
    for rule in rules:
        proto = rule.get("IpProtocol", "")
        if proto == "-1":
            port_str = "All traffic"
        elif rule.get("FromPort") == rule.get("ToPort"):
            port_str = f"{rule['FromPort']}/{proto}"
        else:
            port_str = f"{rule.get('FromPort')}-{rule.get('ToPort')}/{proto}"

        # Collect all sources/destinations
        sources = []
        for cidr in rule.get("IpRanges", []):
            desc = cidr.get("Description", "")
            label = f"{cidr['CidrIp']}"
            if desc:
                label += f" ({desc})"
            sources.append(label)
        for cidr in rule.get("Ipv6Ranges", []):
            desc = cidr.get("Description", "")
            label = f"{cidr['CidrIpv6']}"
            if desc:
                label += f" ({desc})"
            sources.append(label)
        for sg_ref in rule.get("UserIdGroupPairs", []):
            desc = sg_ref.get("Description", "")
            label = f"{sg_ref['GroupId']}"
            if desc:
                label += f" ({desc})"
            sources.append(label)
        for pl in rule.get("PrefixListIds", []):
            sources.append(pl.get("PrefixListId", ""))

        for src in sources:
            lines.append(f"{src} \u2192 {port_str}")

    return "\n".join(lines) if lines else "None"


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
        sgs = c.describe_security_groups(**kwargs)["SecurityGroups"]
        for sg in sgs:
            sg["_Inbound"] = _format_sg_rules(sg.get("IpPermissions", []))
            sg["_Outbound"] = _format_sg_rules(sg.get("IpPermissionsEgress", []))
        return ResourceTable(
            sgs,
            columns=[("GroupId", "Group ID", "cyan"), ("GroupName", "Name", "green"),
                     ("Tags.Name", "Tag Name", "green"),
                     ("VpcId", "VPC ID", "cyan"),
                     ("_Inbound", "Inbound", "white"),
                     ("_Outbound", "Outbound", "white"),
                     ("Description", "Description")],
            title="Security Groups",
        )

    def _ec2_get_metrics(instance_id, hours=1):
        """Get CloudWatch metrics for an EC2 instance.

        Args:
            instance_id: EC2 instance ID (e.g. 'i-0abc123')
            hours: How many hours back to look (default: 1)

        Returns ResourceTable with CPU, Network, Disk, and Status metrics.
        """
        from datetime import datetime, timedelta, timezone

        cw_client = sm.client("cloudwatch")
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=hours)
        period = max(300, (hours * 3600) // 12)  # ~12 data points

        metrics = [
            ("CPUUtilization", "Percent", "Average"),
            ("NetworkIn", "Bytes", "Sum"),
            ("NetworkOut", "Bytes", "Sum"),
            ("DiskReadOps", "Count", "Sum"),
            ("DiskWriteOps", "Count", "Sum"),
            ("StatusCheckFailed", "Count", "Maximum"),
            ("StatusCheckFailed_Instance", "Count", "Maximum"),
            ("StatusCheckFailed_System", "Count", "Maximum"),
        ]

        rows = []
        for metric_name, unit, stat in metrics:
            resp = cw_client.get_metric_statistics(
                Namespace="AWS/EC2",
                MetricName=metric_name,
                Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
                StartTime=start,
                EndTime=end,
                Period=period,
                Statistics=[stat],
                Unit=unit,
            )
            datapoints = sorted(resp.get("Datapoints", []), key=lambda d: d["Timestamp"])
            if datapoints:
                latest = datapoints[-1]
                val = latest[stat]
                # Format bytes as human-readable
                if unit == "Bytes" and val > 0:
                    for u in ["B", "KB", "MB", "GB"]:
                        if val < 1024:
                            formatted = f"{val:.1f} {u}"
                            break
                        val /= 1024
                    else:
                        formatted = f"{val:.1f} TB"
                elif unit == "Percent":
                    formatted = f"{val:.1f}%"
                else:
                    formatted = f"{val:.0f}"
                rows.append({
                    "Metric": metric_name,
                    "Latest": formatted,
                    "Stat": stat,
                    "Datapoints": len(datapoints),
                    "Timestamp": latest["Timestamp"].strftime("%H:%M:%S"),
                })
            else:
                rows.append({
                    "Metric": metric_name,
                    "Latest": "-",
                    "Stat": stat,
                    "Datapoints": 0,
                    "Timestamp": "-",
                })

        return ResourceTable(rows, columns=[
            ("Metric", "Metric", "cyan"),
            ("Latest", "Latest Value", "bold"),
            ("Stat", "Statistic", "yellow"),
            ("Datapoints", "Points", "dim"),
            ("Timestamp", "Last Updated", "dim"),
        ], title=f"EC2 Metrics: {instance_id} (last {hours}h)")

    def _ec2_get_cpu(instance_id, hours=3):
        """Get CPU utilization history for an EC2 instance.

        Returns a time series of CPU usage at 5-minute intervals.
        """
        from datetime import datetime, timedelta, timezone

        cw_client = sm.client("cloudwatch")
        end = datetime.now(timezone.utc)
        start = end - timedelta(hours=hours)

        resp = cw_client.get_metric_statistics(
            Namespace="AWS/EC2",
            MetricName="CPUUtilization",
            Dimensions=[{"Name": "InstanceId", "Value": instance_id}],
            StartTime=start,
            EndTime=end,
            Period=300,
            Statistics=["Average", "Maximum"],
        )

        datapoints = sorted(resp.get("Datapoints", []), key=lambda d: d["Timestamp"])
        rows = []
        for dp in datapoints:
            rows.append({
                "Time": dp["Timestamp"].strftime("%Y-%m-%d %H:%M"),
                "Average": f"{dp['Average']:.1f}%",
                "Maximum": f"{dp['Maximum']:.1f}%",
            })

        return ResourceTable(rows, columns=[
            ("Time", "Time", "dim"),
            ("Average", "Avg CPU %", "cyan"),
            ("Maximum", "Max CPU %", "bold"),
        ], title=f"CPU Utilization: {instance_id} (last {hours}h)")

    ec2.list_instances = _ec2_list_instances
    ec2.list_vpcs = _ec2_list_vpcs
    ec2.list_subnets = _ec2_list_subnets
    ec2.list_security_groups = _ec2_list_security_groups
    ec2.get_metrics = _ec2_get_metrics
    ec2.get_cpu = _ec2_get_cpu
    namespace["ec2"] = ec2

    # --- VPC (wraps ec2 client, VPC-focused helpers) ---
    vpc = ServiceHelper("vpc", sm.client("ec2"))
    vpc.list_vpcs = _ec2_list_vpcs
    vpc.list_subnets = _ec2_list_subnets
    vpc.list_security_groups = _ec2_list_security_groups
    namespace["vpc"] = vpc

    # --- ASG (Auto Scaling Groups) ---
    asg = ServiceHelper("asg", sm.client("autoscaling"))

    def _asg_list_groups():
        c = sm.client("autoscaling")
        groups = []
        for page in c.get_paginator("describe_auto_scaling_groups").paginate():
            groups.extend(page["AutoScalingGroups"])
        for g in groups:
            g["_Instances"] = len(g.get("Instances", []))
            health = {}
            for inst in g.get("Instances", []):
                h = inst.get("HealthStatus", "Unknown")
                health[h] = health.get(h, 0) + 1
            g["_Health"] = ", ".join(f"{v} {k}" for k, v in health.items()) if health else "-"
        return ResourceTable(groups, columns=[
            ("AutoScalingGroupName", "ASG Name", "green"),
            ("MinSize", "Min", "yellow"),
            ("MaxSize", "Max", "yellow"),
            ("DesiredCapacity", "Desired", "yellow"),
            ("_Instances", "Instances", "cyan"),
            ("_Health", "Health", "bold"),
            ("LaunchTemplate.LaunchTemplateName", "Launch Template"),
            ("AvailabilityZones", "AZs"),
        ], title="Auto Scaling Groups")

    def _asg_list_instances():
        c = sm.client("autoscaling")
        instances = []
        for page in c.get_paginator("describe_auto_scaling_instances").paginate():
            instances.extend(page["AutoScalingInstances"])
        return ResourceTable(instances, columns=[
            ("InstanceId", "Instance ID", "cyan"),
            ("AutoScalingGroupName", "ASG Name", "green"),
            ("LifecycleState", "State", "bold"),
            ("HealthStatus", "Health", "bold"),
            ("InstanceType", "Type", "yellow"),
            ("AvailabilityZone", "AZ"),
        ], title="ASG Instances")

    def _asg_list_activities(asg_name=None):
        c = sm.client("autoscaling")
        kwargs = {"AutoScalingGroupName": asg_name} if asg_name else {}
        activities = []
        for page in c.get_paginator("describe_scaling_activities").paginate(**kwargs):
            activities.extend(page["Activities"])
        return ResourceTable(activities[:50], columns=[
            ("AutoScalingGroupName", "ASG Name", "green"),
            ("StatusCode", "Status", "bold"),
            ("Cause", "Cause"),
            ("StartTime", "Started"),
            ("EndTime", "Ended"),
        ], title="Scaling Activities (last 50)")

    asg.list_groups = _asg_list_groups
    asg.list_instances = _asg_list_instances
    asg.list_activities = _asg_list_activities
    namespace["asg"] = asg

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

    # --- SSO Admin ---
    sso_admin = ServiceHelper("sso_admin", sm.client("sso-admin"))

    def _sso_get_instance_arn():
        """Get the SSO instance ARN (auto-detected)."""
        c = sm.client("sso-admin")
        instances = c.list_instances().get("Instances", [])
        if not instances:
            console.print("[red]No SSO instance found[/red]")
            return None
        return instances[0]["InstanceArn"]

    def _sso_list_permission_sets():
        """List all permission sets with names and details."""
        c = sm.client("sso-admin")
        instance_arn = _sso_get_instance_arn()
        if not instance_arn:
            return ResourceTable([])

        # Get all permission set ARNs
        arns = []
        paginator = c.get_paginator("list_permission_sets")
        for page in paginator.paginate(InstanceArn=instance_arn):
            arns.extend(page.get("PermissionSets", []))

        # Enrich each with describe_permission_set
        sets = []
        for arn in arns:
            detail = c.describe_permission_set(
                InstanceArn=instance_arn,
                PermissionSetArn=arn,
            ).get("PermissionSet", {})
            sets.append(detail)

        return ResourceTable(sets, columns=[
            ("Name", "Name", "green"),
            ("PermissionSetArn", "Permission Set ARN", "cyan"),
            ("Description", "Description"),
            ("SessionDuration", "Session Duration", "yellow"),
            ("CreatedDate", "Created"),
        ], title="SSO Permission Sets")

    def _sso_get_policy(name_or_arn=None):
        """Get the inline policy for a permission set by name or ARN.

        Returns the policy dict. Prints as JSON automatically.
        To get raw dict without printing, use: sso_admin.get_policy("name").data
        """
        import json as _json
        c = sm.client("sso-admin")
        instance_arn = _sso_get_instance_arn()
        if not instance_arn:
            return

        ps_arn = _sso_resolve_permission_set(c, instance_arn, name_or_arn)
        if not ps_arn:
            return

        resp = c.get_inline_policy_for_permission_set(
            InstanceArn=instance_arn,
            PermissionSetArn=ps_arn,
        )
        policy_str = resp.get("InlinePolicy", "")
        if not policy_str:
            console.print("[dim]No inline policy attached[/dim]")
            return {}

        policy = _json.loads(policy_str)
        # Wrap statements as a ResourceTable for consistent display
        statements = policy.get("Statement", [])
        for stmt in statements:
            # Flatten Action/Resource lists for display
            actions = stmt.get("Action", [])
            stmt["_Actions"] = ", ".join(actions) if isinstance(actions, list) else actions
            resources = stmt.get("Resource", [])
            stmt["_Resources"] = ", ".join(resources) if isinstance(resources, list) else resources

        return ResourceTable(statements, columns=[
            ("Sid", "Sid", "cyan"),
            ("Effect", "Effect", "bold"),
            ("_Actions", "Actions", "yellow"),
            ("_Resources", "Resources"),
        ], title=f"Inline Policy: {name_or_arn}")

    def _sso_list_managed_policies(name_or_arn=None):
        """List managed policies attached to a permission set by name or ARN."""
        c = sm.client("sso-admin")
        instance_arn = _sso_get_instance_arn()
        if not instance_arn:
            return ResourceTable([])

        ps_arn = _sso_resolve_permission_set(c, instance_arn, name_or_arn)
        if not ps_arn:
            return ResourceTable([])

        policies = []
        paginator = c.get_paginator("list_managed_policies_in_permission_set")
        for page in paginator.paginate(InstanceArn=instance_arn, PermissionSetArn=ps_arn):
            policies.extend(page.get("AttachedManagedPolicies", []))

        return ResourceTable(policies, columns=[
            ("Name", "Policy Name", "green"),
            ("Arn", "Policy ARN", "cyan"),
        ], title=f"Managed Policies")

    def _sso_list_account_assignments(name_or_arn=None, account_id=None):
        """List account assignments for a permission set."""
        c = sm.client("sso-admin")
        instance_arn = _sso_get_instance_arn()
        if not instance_arn:
            return ResourceTable([])

        ps_arn = _sso_resolve_permission_set(c, instance_arn, name_or_arn)
        if not ps_arn:
            return ResourceTable([])

        if not account_id:
            # Try to get from STS
            account_id = sm.client("sts").get_caller_identity()["Account"]

        assignments = []
        paginator = c.get_paginator("list_account_assignments")
        for page in paginator.paginate(
            InstanceArn=instance_arn,
            PermissionSetArn=ps_arn,
            AccountId=account_id,
        ):
            assignments.extend(page.get("AccountAssignments", []))

        return ResourceTable(assignments, columns=[
            ("PrincipalType", "Principal Type", "yellow"),
            ("PrincipalId", "Principal ID", "cyan"),
            ("PermissionSetArn", "Permission Set ARN"),
            ("AccountId", "Account ID"),
        ], title=f"Account Assignments")

    def _sso_resolve_permission_set(client, instance_arn, name_or_arn):
        """Resolve a permission set name or ARN to an ARN."""
        if name_or_arn and name_or_arn.startswith("arn:"):
            return name_or_arn

        # List all and match by name
        arns = []
        paginator = client.get_paginator("list_permission_sets")
        for page in paginator.paginate(InstanceArn=instance_arn):
            arns.extend(page.get("PermissionSets", []))

        for arn in arns:
            detail = client.describe_permission_set(
                InstanceArn=instance_arn,
                PermissionSetArn=arn,
            ).get("PermissionSet", {})
            if name_or_arn is None:
                console.print(f"[yellow]Please specify a permission set name or ARN[/yellow]")
                return None
            if detail.get("Name", "").lower() == name_or_arn.lower():
                return arn

        console.print(f"[red]Permission set '{name_or_arn}' not found[/red]")
        return None

    sso_admin.list_permission_sets = _sso_list_permission_sets
    sso_admin.get_policy = _sso_get_policy
    sso_admin.list_managed_policies = _sso_list_managed_policies
    sso_admin.list_account_assignments = _sso_list_account_assignments
    namespace["sso_admin"] = sso_admin

    # --- Cache (ElastiCache) ---
    cache = ServiceHelper("cache", sm.client("elasticache"))
    cache.list_clusters = _paginated_helper(
        sm, "elasticache", "describe_cache_clusters", "CacheClusters",
        columns=[("CacheClusterId", "Cluster ID"), ("CacheNodeType", "Node Type"),
                 ("Engine", "Engine"), ("CacheClusterStatus", "Status")],
        title="ElastiCache Clusters")
    cache.list_replication_groups = _paginated_helper(
        sm, "elasticache", "describe_replication_groups", "ReplicationGroups",
        columns=[("ReplicationGroupId", "Replication Group ID"), ("Description", "Description"),
                 ("Status", "Status"), ("ClusterEnabled", "Cluster Enabled")],
        title="ElastiCache Replication Groups")

    def _cache_list_serverless():
        c = sm.client("elasticache")
        resp = c.describe_serverless_caches()
        items = resp.get("ServerlessCaches", [])
        return ResourceTable(items, columns=[
            ("ServerlessCacheName", "Name"),
            ("Engine", "Engine"),
            ("MajorEngineVersion", "Version"),
            ("Status", "Status"),
            ("ARN", "ARN"),
        ], title="ElastiCache Serverless Caches")

    cache.list_serverless = _cache_list_serverless
    namespace["cache"] = cache

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
