"""Unit tests for DatabaseManager and sample database generation."""

import sqlite3
import tempfile
from pathlib import Path
import pytest
from src.database.db_manager import DatabaseManager
from src.database.sample_data import create_sample_database


import gc

@pytest.fixture
def temp_db():
    """Creates a temporary sample enterprise database."""
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp_dir:
        db_path = Path(tmp_dir) / "test_enterprise.db"
        create_sample_database(db_path)
        yield db_path
        gc.collect()


def test_sample_database_generation(temp_db):
    assert temp_db.exists()
    assert temp_db.stat().st_size > 0


def test_get_tables(temp_db):
    manager = DatabaseManager(temp_db)
    tables = manager.get_tables()
    expected = ["customers", "departments", "employees", "order_items", "orders", "products"]
    for tbl in expected:
        assert tbl in tables


def test_get_table_schema(temp_db):
    manager = DatabaseManager(temp_db)
    schema = manager.get_table_schema("employees")
    assert schema["table_name"] == "employees"
    assert schema["row_count"] >= 15
    col_names = [col["name"] for col in schema["columns"]]
    assert "employee_id" in col_names
    assert "salary" in col_names
    assert "department_id" in col_names


def test_formatted_schema_for_llm(temp_db):
    manager = DatabaseManager(temp_db)
    schema_text = manager.get_formatted_schema_for_llm()
    assert "Table: employees" in schema_text
    assert "Foreign Key:" in schema_text
    assert "Example row:" in schema_text


def test_execute_valid_query(temp_db):
    manager = DatabaseManager(temp_db)
    result = manager.execute_query("SELECT count(*) AS total FROM employees;")
    assert result.success is True
    assert result.error is None
    assert result.columns == ["total"]
    assert result.rows[0][0] >= 15
    assert result.execution_time_ms >= 0


def test_execute_invalid_query(temp_db):
    manager = DatabaseManager(temp_db)
    result = manager.execute_query("SELECT nonexistent_col FROM employees;")
    assert result.success is False
    assert result.error is not None
    assert "no such column" in result.error.lower()


def test_import_csv(temp_db):
    manager = DatabaseManager(temp_db)
    import io
    csv_data = io.StringIO("id,name,role\n1,Alice,Engineer\n2,Bob,Analyst\n")
    count = manager.import_csv_to_table(csv_data, "contractors")
    assert count == 2
    assert "contractors" in manager.get_tables()
