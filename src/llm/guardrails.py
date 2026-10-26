"""Security guardrails and query validation for Text-to-SQL generation."""

import re
from typing import Tuple
try:
    import sqlparse
except ImportError:
    sqlparse = None


# Forbidden keywords in read-only mode to prevent mutation or destructive operations
FORBIDDEN_KEYWORDS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bUPDATE\b",
    r"\bINSERT\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bCREATE\b",
    r"\bREPLACE\b",
    r"\bATTACH\b",
    r"\bDETACH\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
]

COMPILED_FORBIDDEN = [re.compile(kw, re.IGNORECASE) for kw in FORBIDDEN_KEYWORDS]


def validate_sql_query(sql: str, read_only: bool = True) -> Tuple[bool, str]:
    """Validates that a SQL query is safe to execute.
    
    Returns:
        (is_valid, error_message)
    """
    if not sql or not sql.strip():
        return False, "Query is empty."

    cleaned_sql = sql.strip().rstrip(";")

    if read_only:
        for pattern in COMPILED_FORBIDDEN:
            match = pattern.search(cleaned_sql)
            if match:
                keyword = match.group(0).upper()
                return (
                    False,
                    f"Security Guardrail Violation: Destructive operation '{keyword}' is prohibited in read-only mode.",
                )

        # Ensure the query begins with a read-only keyword (SELECT, WITH, EXPLAIN, PRAGMA)
        first_token = cleaned_sql.split()[0].upper() if cleaned_sql.split() else ""
        allowed_starts = ("SELECT", "WITH", "EXPLAIN", "PRAGMA")
        if first_token not in allowed_starts:
            return (
                False,
                f"Security Guardrail Violation: Query must start with SELECT, WITH, or EXPLAIN (got '{first_token}').",
            )

    return True, ""


def format_sql(sql: str) -> str:
    """Formats SQL nicely with indentation and uppercase keywords."""
    if not sql:
        return ""
    if sqlparse:
        return sqlparse.format(
            sql.strip(),
            reindent=True,
            keyword_case="upper",
            identifier_case="lower",
        )
    return sql.strip()
