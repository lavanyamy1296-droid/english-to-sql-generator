"""Self-healing agent that analyzes SQLite execution errors and repairs queries."""

from typing import Any, Dict
from src.llm.guardrails import format_sql
from src.llm.prompts import SELF_HEALING_PROMPT
from src.llm.sql_generator import SQLGenerator


def heal_sql_query(
    failed_sql: str,
    error_message: str,
    schema_context: str,
    natural_language_query: str,
    generator: SQLGenerator,
) -> Dict[str, Any]:
    """Sends the failed SQL, execution error, and schema to the LLM to diagnose and repair."""
    user_prompt = f"""### DATABASE SCHEMA:
{schema_context}

### ORIGINAL USER QUESTION:
"{natural_language_query}"

### FAILED SQL QUERY:
```sql
{failed_sql}
```

### DATABASE EXECUTION ERROR:
"{error_message}"

Diagnose the error against the schema, repair the SQL query, and provide a clear explanation.
"""

    if generator.provider == "groq":
        raw_output = generator._call_groq(f"{SELF_HEALING_PROMPT}\n\n{user_prompt}")
    elif generator.provider == "gemini":
        raw_output = generator._call_gemini(f"{SELF_HEALING_PROMPT}\n\n{user_prompt}")
    elif generator.provider == "openai":
        raw_output = generator._call_openai(f"{SELF_HEALING_PROMPT}\n\n{user_prompt}")
    else:
        raise ValueError(f"Unsupported provider: {generator.provider}")

    parsed = generator._parse_llm_response(raw_output)
    raw_sql = parsed.get("sql", "").strip()
    formatted = format_sql(raw_sql)

    return {
        "sql": formatted or raw_sql,
        "raw_sql": raw_sql,
        "explanation": parsed.get("explanation", "Repaired query based on database error."),
        "error_cause": parsed.get("error_cause", error_message),
        "healed": True,
    }
