"""Output formatting utilities."""
import json
from datetime import datetime, date

from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax

console = Console()


class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


def print_json(data):
    json_str = json.dumps(data, indent=2, cls=DateTimeEncoder, default=str)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
    console.print(syntax)


def print_table(title, columns, rows):
    table = Table(title=title)
    for col in columns:
        table.add_column(col["name"], style=col.get("style", ""))
    for row in rows:
        table.add_row(*[str(row.get(col["name"], "")) for col in columns])
    console.print(table)
