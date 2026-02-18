"""Generic AWS pagination helper."""


def paginate_all(client, method_name, result_key, **kwargs):
    try:
        paginator = client.get_paginator(method_name)
        results = []
        for page in paginator.paginate(**kwargs):
            results.extend(page.get(result_key, []))
        return results
    except Exception:
        results = []
        response = getattr(client, method_name)(**kwargs)
        results.extend(response.get(result_key, []))
        while response.get("NextToken"):
            response = getattr(client, method_name)(
                NextToken=response["NextToken"], **kwargs
            )
            results.extend(response.get(result_key, []))
        return results
