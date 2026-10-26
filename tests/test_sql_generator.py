"""Unit tests for SQLGenerator response parsing and prompt formatting."""

import pytest
from src.llm.sql_generator import SQLGenerator


def test_parse_clean_json():
    gen = SQLGenerator(provider="groq", api_key="dummy")
    raw = '{"sql": "SELECT * FROM employees;", "explanation": "Returns all employees.", "assumptions": ""}'
    parsed = gen._parse_llm_response(raw)
    assert parsed["sql"] == "SELECT * FROM employees;"
    assert "Returns all employees" in parsed["explanation"]


def test_parse_json_in_markdown_code_block():
    gen = SQLGenerator(provider="groq", api_key="dummy")
    raw = """```json
{
    "sql": "SELECT name, budget FROM departments WHERE budget > 500000;",
    "explanation": "Filters departments with high budget.",
    "assumptions": "None"
}
```"""
    parsed = gen._parse_llm_response(raw)
    assert "departments" in parsed["sql"]
    assert "budget" in parsed["sql"]


def test_parse_raw_sql_fallback():
    gen = SQLGenerator(provider="groq", api_key="dummy")
    raw = "Here is the query you need: SELECT id, name FROM customers ORDER BY name ASC;"
    parsed = gen._parse_llm_response(raw)
    assert "SELECT id, name FROM customers" in parsed["sql"]
