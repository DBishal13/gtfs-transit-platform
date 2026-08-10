"""Documents and enforces this service's SQL-safety rule: **all values are passed as bound
psycopg parameters (%(name)s in the query text, a dict at execute() time) — never
string-interpolated into SQL.** See service/app/services/geo_service.py for the pattern
every service module should follow.

The one case where raw text must be spliced into a SQL statement is a dynamic
*identifier* (a table or column name — parameters can only bind values, not identifiers).
No query in this codebase needs that today. If one ever does, route the identifier through
`assert_safe_identifier` below rather than interpolating it directly.
"""

from __future__ import annotations

import re

_IDENTIFIER_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def assert_safe_identifier(name: str) -> str:
    """Raise ValueError unless `name` is a plain alphanumeric/underscore identifier,
    otherwise return it unchanged. Only for identifiers, never for values."""
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Unsafe SQL identifier: {name!r}")
    return name
