"""Fuzzy search utilities for AWS resource configurations."""


def flatten_json(data, prefix=""):
    """Recursively flatten a nested dict/list into key-path -> value pairs."""
    items = []
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, (dict, list)):
                items.extend(flatten_json(value, path))
            else:
                items.append((path, str(value)))
    elif isinstance(data, list):
        for i, value in enumerate(data):
            path = f"{prefix}[{i}]"
            if isinstance(value, (dict, list)):
                items.extend(flatten_json(value, path))
            else:
                items.append((path, str(value)))
    else:
        items.append((prefix, str(data)))
    return items


def fuzzy_search(data, keyword):
    """Search flattened JSON for keyword matches in paths or values.

    Returns list of (path, value) tuples where keyword appears
    (case-insensitive substring match).
    """
    keyword_lower = keyword.lower()
    flat = flatten_json(data)
    results = []
    for path, value in flat:
        if keyword_lower in path.lower() or keyword_lower in value.lower():
            results.append((path, value))
    return results
