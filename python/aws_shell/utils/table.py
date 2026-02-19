"""ResourceTable - tabular display wrapper for AWS resource data."""
import json
import re
from datetime import datetime, date

from rich.console import Console
from rich.table import Table

console = Console()

# Known status/state values and their colors
_STATUS_COLORS = {
    # EC2 / general
    "running": "green",
    "available": "green",
    "active": "green",
    "enabled": "green",
    "in-use": "green",
    "deployed": "green",
    "complete": "green",
    "create_complete": "green",
    "update_complete": "green",
    "ok": "green",
    "healthy": "green",
    "true": "green",
    # Warning states
    "pending": "yellow",
    "modifying": "yellow",
    "updating": "yellow",
    "in_progress": "yellow",
    "create_in_progress": "yellow",
    "update_in_progress": "yellow",
    "shutting-down": "yellow",
    "stopping": "yellow",
    "creating": "yellow",
    "deleting": "yellow",
    "insufficient_data": "yellow",
    # Stopped/inactive
    "stopped": "red",
    "terminated": "dim",
    "deleted": "dim",
    "disabled": "dim",
    "inactive": "dim",
    "failed": "red",
    "error": "red",
    "alarm": "red",
    "delete_failed": "red",
    "rollback_complete": "red",
    "false": "red",
}

# Regex patterns for value-based highlighting
_IP_PATTERN = re.compile(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
_ARN_PATTERN = re.compile(r"^arn:")
_ID_PATTERN = re.compile(r"^(i|vpc|subnet|sg|vol|snap|ami|rtb|igw|nat|eni|acl)-[0-9a-f]+$")
_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _get_value(item, key):
    """Get a value from a dict, handling nested keys and AWS Tags.

    Supports:
        'InstanceId'       -> item['InstanceId']
        'State.Name'       -> item['State']['Name']
        'Tags.Name'        -> extracts Name tag from Tags list
    """
    if not isinstance(item, dict):
        return item

    if key.startswith("Tags."):
        tag_name = key[5:]
        tags = item.get("Tags") or []
        for tag in tags:
            if isinstance(tag, dict) and tag.get("Key") == tag_name:
                return tag.get("Value", "")
        return ""

    parts = key.split(".")
    current = item
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def _format_cell(value):
    """Format a cell value for table display, plain text."""
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, (dict, list)):
        s = str(value)
        return s[:60] + "..." if len(s) > 60 else s
    s = str(value)
    return s[:80] + "..." if len(s) > 80 else s


def _highlight_cell(value):
    """Format a cell value with Rich markup for smart syntax highlighting."""
    if value is None:
        return ""
    if isinstance(value, (datetime, date)):
        return f"[dim]{value.isoformat()}[/dim]"
    if isinstance(value, bool):
        color = "green" if value else "red"
        return f"[{color}]{value}[/{color}]"
    if isinstance(value, (dict, list)):
        s = str(value)
        s = s[:60] + "..." if len(s) > 60 else s
        return f"[dim]{s}[/dim]"

    s = str(value)
    s = s[:80] + "..." if len(s) > 80 else s

    # Check for known status/state values
    color = _STATUS_COLORS.get(s.lower())
    if color:
        return f"[{color}]{s}[/{color}]"

    # AWS resource IDs
    if _ID_PATTERN.match(s):
        return f"[cyan]{s}[/cyan]"

    # ARNs
    if _ARN_PATTERN.match(s):
        return f"[dim cyan]{s}[/dim cyan]"

    # IP addresses
    if _IP_PATTERN.match(s):
        return f"[blue]{s}[/blue]"

    # Dates
    if _DATE_PATTERN.match(s):
        return f"[dim]{s}[/dim]"

    return s


class _DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


# Column style presets for common column types
_COLUMN_STYLES = {
    "id": "cyan",
    "name": "green",
    "type": "yellow",
    "status": "bold",
    "state": "bold",
}


def _guess_column_style(header_lower):
    """Guess a column style from the header name."""
    for keyword, style in _COLUMN_STYLES.items():
        if keyword in header_lower:
            return style
    return "white"


_METHOD_DOCS = {
    "filter": (
        '.filter(key="value") or .filter(lambda i: ...)',
        "Filter rows with exact match (case-insensitive). Use * for wildcards.\n\n"
        "Examples:\n"
        '  .filter(Name="swe-permission-set")   # exact match\n'
        '  .filter(Name="*swe*")                # contains "swe"\n'
        '  .filter(Name="*swe")                 # ends with "swe"\n'
        '  .filter(InstanceType="t3*")          # starts with "t3"\n'
        '  .filter(State="running")             # exact match\n'
        "  .filter(lambda i: i['InstanceType'].startswith('t3'))"
    ),
    "find": (
        '.find("keyword")',
        "Fuzzy search across ALL fields. Returns rows where any value matches.\n\n"
        "Examples:\n"
        '  .find("production")    # search all fields\n'
        '  .find("10.0.1")       # find by IP fragment\n'
        '  .find("docker")       # find by keyword'
    ),
    "sort": (
        '.sort("key", reverse=False)',
        "Sort rows by a column key. Supports nested keys and Tags.\n\n"
        "Examples:\n"
        '  .sort("Tags.Name")                    # sort by name tag\n'
        '  .sort("LaunchTime", reverse=True)     # newest first'
    ),
    "select": (
        '.select("key:Header", ...)',
        "Choose which columns to display. Use 'key' or 'key:Header' format.\n\n"
        "Examples:\n"
        '  .select("InstanceId:ID", "Tags.Name:Name", "State.Name:State")'
    ),
    "json": (
        ".json()",
        "Pretty-print all data as formatted, syntax-highlighted JSON."
    ),
    "help": (
        ".help()",
        "Show overview of all available ResourceTable methods."
    ),
}


class _DocMethod:
    """Wraps a ResourceTable method so it's callable AND has .docs."""

    def __init__(self, method, name):
        self._method = method
        self._name = name

    def __call__(self, *args, **kwargs):
        return self._method(*args, **kwargs)

    @property
    def docs(self):
        info = _METHOD_DOCS.get(self._name)
        if info:
            sig, doc = info
            console.print(f"\n[bold cyan]{sig}[/bold cyan]\n\n{doc}\n")
        else:
            console.print(f"[dim]No docs for .{self._name}[/dim]")

    def __repr__(self):
        return f"<.{self._name}() method — call .docs for help>"


class ResourceTable:
    """A list of resource dicts that renders as a Rich table.

    Returned by ServiceHelper methods in the Python REPL.
    Auto-renders as a table when evaluated as an expression.

    Column specs can be:
        ("key", "Header")              - auto-style based on header name
        ("key", "Header", "cyan")      - explicit column style

    Methods:
        .filter(fn) or .filter(Key="value")  - Filter rows
        .sort("key")                          - Sort by key
        .find("keyword")                      - Fuzzy search
        .select("key1", "key2:Header")        - Choose display columns
        .data                                 - Raw list of dicts
        .json()                               - Print as JSON
        [0], [1:5], len()                     - Indexing & slicing

    Tip: access any method without () to see .docs, e.g. .filter.docs
    """

    _DOC_METHODS = frozenset({"filter", "find", "sort", "select", "json", "help"})

    def __getattribute__(self, name):
        attr = object.__getattribute__(self, name)
        if name in ResourceTable._DOC_METHODS and callable(attr):
            return _DocMethod(attr, name)
        return attr

    def __init__(self, data, columns=None, title=None):
        self._data = data if isinstance(data, list) else list(data)
        self._columns = columns  # list of (key, header) or (key, header, style)
        self._title = title

    def render(self):
        """Render as a Rich table to the console."""
        if not self._data:
            console.print("[dim]No results[/dim]")
            return

        table = Table(title=self._title, show_lines=False)

        if self._columns:
            for col in self._columns:
                key, header = col[0], col[1]
                style = col[2] if len(col) > 2 else _guess_column_style(header.lower())
                table.add_column(header, style=style, overflow="fold")
            for item in self._data:
                row = [_highlight_cell(_get_value(item, col[0])) for col in self._columns]
                table.add_row(*row)
        elif isinstance(self._data[0], dict):
            # Auto-detect columns from keys
            keys = list(self._data[0].keys())
            keys = [k for k in keys if k not in ("ResponseMetadata",)][:10]
            for key in keys:
                style = _guess_column_style(key.lower())
                table.add_column(key, style=style, overflow="fold", max_width=40)
            for item in self._data:
                row = [_highlight_cell(item.get(k)) for k in keys]
                table.add_row(*row)
        else:
            # Simple list of strings/numbers
            table.add_column("Value", style="cyan")
            for item in self._data:
                table.add_row(str(item))

        console.print(table)
        console.print(f"[dim]{len(self._data)} item(s)[/dim]")

    def filter(self, fn=None, **kwargs):
        """Filter rows by function or keyword arguments.

        Exact match (case-insensitive) by default.
        Use * for wildcard/contains matching.
        Supports nested keys (State.Name) and auto-checks Tags.

        Examples:
            .filter(Name="swe-permission-set")   # exact match
            .filter(Name="*swe*")                 # contains "swe"
            .filter(Name="*swe")                  # ends with "swe"
            .filter(Name="swe*")                  # starts with "swe"
            .filter(State="running")              # exact match
            .filter(InstanceType="t3*")           # starts with "t3"
            .filter(lambda i: i['InstanceType'].startswith('t3'))
        """
        if fn is not None:
            filtered = [item for item in self._data if fn(item)]
        else:
            filtered = self._data
            for key, value in kwargs.items():
                result = []
                value_str = str(value)
                value_lower = value_str.lower()

                # Determine match mode from wildcards
                has_prefix_star = value_str.startswith("*")
                has_suffix_star = value_str.endswith("*")
                # Strip wildcards for the actual comparison value
                match_val = value_lower.lstrip("*").rstrip("*")

                for item in filtered:
                    if not isinstance(item, dict):
                        continue
                    # Try: direct key, nested path, then Tags.Key fallback
                    item_val = _get_value(item, key)
                    if item_val is None:
                        item_val = _get_value(item, f"Tags.{key}")
                    if item_val is None:
                        continue

                    if isinstance(item_val, (dict, list)):
                        # For complex types, always use contains matching
                        vals = item_val.values() if isinstance(item_val, dict) else item_val
                        if any(match_val in str(v).lower() for v in vals):
                            result.append(item)
                    else:
                        item_str = str(item_val).lower()
                        if has_prefix_star and has_suffix_star:
                            # *value* → contains
                            if match_val in item_str:
                                result.append(item)
                        elif has_prefix_star:
                            # *value → ends with
                            if item_str.endswith(match_val):
                                result.append(item)
                        elif has_suffix_star:
                            # value* → starts with
                            if item_str.startswith(match_val):
                                result.append(item)
                        else:
                            # exact match (case-insensitive)
                            if item_str == match_val:
                                result.append(item)
                filtered = result
        return ResourceTable(filtered, columns=self._columns, title=self._title)

    def sort(self, key, reverse=False):
        """Sort rows by key.

        Example: .sort("LaunchTime", reverse=True)
        """
        sorted_data = sorted(
            self._data,
            key=lambda x: str(_get_value(x, key) or ""),
            reverse=reverse,
        )
        return ResourceTable(sorted_data, columns=self._columns, title=self._title)

    def find(self, keyword):
        """Fuzzy search all fields for keyword matches.

        Example: .find("production")
        """
        from .search import flatten_json

        keyword_lower = keyword.lower()
        matching = []
        for item in self._data:
            if isinstance(item, dict):
                flat = flatten_json(item)
                if any(
                    keyword_lower in v.lower() or keyword_lower in p.lower()
                    for p, v in flat
                ):
                    matching.append(item)
            elif keyword_lower in str(item).lower():
                matching.append(item)
        return ResourceTable(
            matching, columns=self._columns, title=f"Search: '{keyword}'"
        )

    def select(self, *keys):
        """Choose which columns to display.

        Use 'key' or 'key:Header' format.
        Example: .select("InstanceId:ID", "State.Name:State", "Tags.Name:Name")
        """
        col_specs = []
        for col in keys:
            if ":" in col:
                k, h = col.split(":", 1)
                col_specs.append((k.strip(), h.strip()))
            else:
                col_specs.append((col.strip(), col.strip()))
        return ResourceTable(self._data, columns=col_specs, title=self._title)

    @property
    def data(self):
        """Get raw list of dicts."""
        return self._data

    def json(self):
        """Print data as formatted JSON."""
        from rich.syntax import Syntax

        json_str = json.dumps(self._data, indent=2, cls=_DateTimeEncoder, default=str)
        syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
        console.print(syntax)

    def help(self):
        """Show available ResourceTable methods with examples."""
        from rich.panel import Panel

        console.print(Panel(
            "[bold cyan].filter[/bold cyan](key=\"value\")  or  .filter(lambda i: ...)\n"
            "  Contains match (case-insensitive). Auto-checks Tags.\n"
            "  [dim]ec2.list_instances().filter(State=\"running\")\n"
            "  ec2.list_instances().filter(Name=\"web\")\n"
            "  ec2.list_instances().filter(InstanceType=\"t3\")\n"
            "  ec2.list_instances().filter(lambda i: i[\"InstanceType\"].startswith(\"t3\"))[/dim]\n\n"
            "[bold cyan].find[/bold cyan](\"keyword\")\n"
            "  Fuzzy search across all fields. Returns matching rows.\n"
            "  [dim]ec2.list_instances().find(\"production\")[/dim]\n\n"
            "[bold cyan].sort[/bold cyan](\"key\", reverse=False)\n"
            "  Sort rows by column. Supports nested keys and Tags.\n"
            "  [dim]ec2.list_instances().sort(\"Tags.Name\")\n"
            "  ec2.list_instances().sort(\"LaunchTime\", reverse=True)[/dim]\n\n"
            "[bold cyan].select[/bold cyan](\"key:Header\", ...)\n"
            "  Choose which columns to display.\n"
            "  [dim]ec2.list_instances().select(\"InstanceId:ID\", \"Tags.Name:Name\", \"State.Name:State\")[/dim]\n\n"
            "[bold cyan].data[/bold cyan]\n"
            "  Raw list of dicts (JSON output).\n"
            "  [dim]ec2.list_instances().data[/dim]\n\n"
            "[bold cyan].json[/bold cyan]()\n"
            "  Pretty-print as formatted JSON.\n"
            "  [dim]ec2.list_instances().json()[/dim]\n\n"
            "[bold cyan].help[/bold cyan]()\n"
            "  Show this help.\n\n"
            "[bold]Chaining:[/bold] all methods return a new table so you can chain them:\n"
            "  [dim]ec2.list_instances().filter(State=\"running\").find(\"web\").sort(\"Tags.Name\")[/dim]\n\n"
            "[bold]Slicing:[/bold]\n"
            "  [dim]ec2.list_instances()[:10]     # first 10 rows\n"
            "  ec2.list_instances()[0]       # first row as dict\n"
            "  len(ec2.list_instances())     # row count[/dim]",
            title="ResourceTable Methods",
            border_style="cyan",
        ))

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __getitem__(self, idx):
        if isinstance(idx, slice):
            return ResourceTable(
                self._data[idx], columns=self._columns, title=self._title
            )
        return self._data[idx]

    def __repr__(self):
        return f"ResourceTable({len(self._data)} items — use .data for raw, .json() for JSON)"

    def __bool__(self):
        return bool(self._data)
