"""Unit tests for SQL guardrails and query safety."""

import pytest
from src.llm.guardrails import format_sql, validate_sql_query


def test_validate_safe_select():
    sql = "SELECT first_name, last_name FROM employees WHERE salary > 50000;"
    is_safe, err = validate_sql_query(sql, read_only=True)
    assert is_safe is True
    assert err == ""


def test_validate_safe_with_cte():
    sql = """
    WITH dept_avg AS (
        SELECT department_id, AVG(salary) AS avg_sal FROM employees GROUP BY department_id
    )
    SELECT * FROM dept_avg;
    """
    is_safe, err = validate_sql_query(sql, read_only=True)
    assert is_safe is True
    assert err == ""


def test_validate_blocks_drop():
    sql = "DROP TABLE employees;"
    is_safe, err = validate_sql_query(sql, read_only=True)
    assert is_safe is False
    assert "Destructive operation 'DROP' is prohibited" in err


def test_validate_blocks_delete():
    sql = "DELETE FROM customers WHERE customer_id = 1;"
    is_safe, err = validate_sql_query(sql, read_only=True)
    assert is_safe is False
    assert "Destructive operation 'DELETE' is prohibited" in err


def test_validate_blocks_update():
    sql = "UPDATE employees SET salary = salary * 2;"
    is_safe, err = validate_sql_query(sql, read_only=True)
    assert is_safe is False
    assert "Destructive operation 'UPDATE' is prohibited" in err


def test_validate_blocks_insert():
    sql = "INSERT INTO departments (name, budget, location) VALUES ('Security', 100000, 'Floor 1');"
    is_safe, err = validate_sql_query(sql, read_only=True)
    assert is_safe is False
    assert "Destructive operation 'INSERT' is prohibited" in err


def test_format_sql():
    raw = "select id, name from users where active=1 order by id desc"
    formatted = format_sql(raw)
    assert "SELECT" in formatted
    assert "FROM" in formatted
    assert "ORDER BY" in formatted
