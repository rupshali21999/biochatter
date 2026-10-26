"""Report which data sources a generated Cypher query draws on.

Works with KGs whose nodes and relationships carry a `data_sources` list
property (e.g. ["pilot"], ["CKG"]). The query is not changed; its labels and
relationship types are looked up in the graph instead.
"""

import re
from collections.abc import Callable

_NODE_LABEL = re.compile(r"\(\s*\w*\s*:\s*`?(\w+)")
_REL_TYPES = re.compile(r"\[\s*\w*\s*:\s*([\w|:`\s]+)")


def query_elements(query: str) -> tuple[list[str], list[str]]:
    """Return the node labels and relationship types used in a Cypher query."""
    labels = list(dict.fromkeys(_NODE_LABEL.findall(query)))
    rel_types = []
    for group in _REL_TYPES.findall(query):
        for rel_type in group.split("|"):
            rel_type = rel_type.strip(" `:\n\t")
            if rel_type and rel_type not in rel_types:
                rel_types.append(rel_type)
    return labels, rel_types


def query_sources(query: str, run: Callable[[str], list[dict]]) -> dict[str, list[str]]:
    """Map each data source to the query elements that come from it.

    Relationships carry the facts a query returns, so when the query uses
    any, sources are attributed through them alone; node labels shared by
    several sources (e.g. a disease in both datasets) would otherwise
    over-report. Queries without relationship types fall back to labels.

    Args:
        query: the Cypher query that produced the results
        run:   executes a Cypher string and returns rows as dicts

    Returns:
        {source: [label or relationship type, ...]}, empty if the graph has
        no `data_sources` on the matched elements
    """
    labels, rel_types = query_elements(query)
    if rel_types:
        patterns = [(t, f"MATCH ()-[x:`{t}`]->()") for t in rel_types]
    else:
        patterns = [(label, f"MATCH (x:`{label}`)") for label in labels]

    sources: dict[str, list[str]] = {}
    for name, pattern in patterns:
        rows = run(f"{pattern} UNWIND x.data_sources AS source RETURN DISTINCT source")
        for row in rows:
            sources.setdefault(row["source"], []).append(name)
    return sources
