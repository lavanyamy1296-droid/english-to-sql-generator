"""Database management, schema introspection, and safe query execution."""

import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd


class QueryResult:
    """Represents the outcome of a SQL execution."""

    def __init__(
        self,
        success: bool,
        sql: str,
        columns: Optional[List[str]] = None,
        rows: Optional[List[Tuple[Any, ...]]] = None,
        row_count: int = 0,
        execution_time_ms: float = 0.0,
        error: Optional[str] = None,
    ):
        self.success = success
        self.sql = sql
        self.columns = columns or []
        self.rows = rows or []
        self.row_count = row_count
        self.execution_time_ms = execution_time_ms
        self.error = error

    def to_dataframe(self) -> pd.DataFrame:
        """Converts results to a pandas DataFrame."""
        if not self.columns or not self.rows:
            return pd.DataFrame()
        return pd.DataFrame(self.rows, columns=self.columns)


class DatabaseManager:
    """Handles database schema extraction, CSV loading, and query execution."""

    def __init__(self, db_path: Union[str, Path]):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Creates a connection with foreign keys enabled."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def get_tables(self) -> List[str]:
        """Returns all user table names in the database."""
        if not self.db_path.exists():
            return []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
            )
            return [row[0] for row in cursor.fetchall()]

    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Extracts schema, primary/foreign keys, row count, and sample data for a table."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Columns info: cid, name, type, notnull, dflt_value, pk
            cursor.execute(f"PRAGMA table_info('{table_name}');")
            columns_raw = cursor.fetchall()
            columns = [
                {
                    "cid": col[0],
                    "name": col[1],
                    "type": col[2] or "TEXT",
                    "notnull": bool(col[3]),
                    "default": col[4],
                    "is_pk": bool(col[5]),
                }
                for col in columns_raw
            ]

            # Foreign keys: id, seq, table, from, to, on_update, on_delete, match
            cursor.execute(f"PRAGMA foreign_key_list('{table_name}');")
            fks_raw = cursor.fetchall()
            foreign_keys = [
                {"from_col": fk[3], "to_table": fk[2], "to_col": fk[4]}
                for fk in fks_raw
            ]

            # Row count
            cursor.execute(f"SELECT COUNT(*) FROM '{table_name}';")
            row_count = cursor.fetchone()[0]

            # Sample rows (first 3)
            cursor.execute(f"SELECT * FROM '{table_name}' LIMIT 3;")
            sample_rows = cursor.fetchall()

            return {
                "table_name": table_name,
                "columns": columns,
                "foreign_keys": foreign_keys,
                "row_count": row_count,
                "sample_rows": sample_rows,
            }

    def get_full_schema(self) -> Dict[str, Dict[str, Any]]:
        """Returns the full schema metadata dictionary for all tables."""
        tables = self.get_tables()
        return {tbl: self.get_table_schema(tbl) for tbl in tables}

    def get_formatted_schema_for_llm(self) -> str:
        """Formats the database schema into a compact, crystal-clear prompt context for the LLM."""
        tables = self.get_tables()
        if not tables:
            return "No tables found in database."

        schema_lines = []
        for table in tables:
            info = self.get_table_schema(table)
            cols_desc = []
            for col in info["columns"]:
                pk_flag = " [PRIMARY KEY]" if col["is_pk"] else ""
                cols_desc.append(f"  - {col['name']} ({col['type']}){pk_flag}")

            fk_desc = []
            for fk in info["foreign_keys"]:
                fk_desc.append(f"  * Foreign Key: {fk['from_col']} -> {fk['to_table']}({fk['to_col']})")

            # Sample row preview for context
            sample_preview = ""
            if info["sample_rows"]:
                sample_col_names = [c["name"] for c in info["columns"]]
                first_row = [str(val) for val in info["sample_rows"][0]]
                sample_preview = f"  * Example row: {dict(zip(sample_col_names, first_row))}"

            table_block = [f"Table: {table} ({info['row_count']} rows)"]
            table_block.extend(cols_desc)
            if fk_desc:
                table_block.extend(fk_desc)
            if sample_preview:
                table_block.append(sample_preview)

            schema_lines.append("\n".join(table_block))

        return "\n\n".join(schema_lines)

    def execute_query(
        self,
        sql: str,
        max_rows: int = 500,
        timeout_seconds: float = 10.0,
    ) -> QueryResult:
        """Executes a SQL query safely, returning columns, rows, timing, or error message."""
        sql_clean = sql.strip().rstrip(";")
        start_time = time.perf_counter()

        try:
            with sqlite3.connect(str(self.db_path), timeout=timeout_seconds) as conn:
                cursor = conn.cursor()
                cursor.execute(sql_clean)

                # If SELECT query or query with result set
                if cursor.description:
                    columns = [desc[0] for desc in cursor.description]
                    rows = cursor.fetchmany(max_rows)
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                    return QueryResult(
                        success=True,
                        sql=sql_clean,
                        columns=columns,
                        rows=rows,
                        row_count=len(rows),
                        execution_time_ms=round(elapsed_ms, 2),
                    )
                else:
                    conn.commit()
                    elapsed_ms = (time.perf_counter() - start_time) * 1000.0
                    return QueryResult(
                        success=True,
                        sql=sql_clean,
                        columns=["Status"],
                        rows=[(f"Query executed successfully ({cursor.rowcount} rows affected)",)],
                        row_count=cursor.rowcount,
                        execution_time_ms=round(elapsed_ms, 2),
                    )

        except Exception as exc:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return QueryResult(
                success=False,
                sql=sql_clean,
                error=str(exc),
                execution_time_ms=round(elapsed_ms, 2),
            )

    def import_csv_to_table(
        self,
        csv_file_or_path: Any,
        table_name: str,
        if_exists: str = "replace"
    ) -> int:
        """Imports a CSV file or uploaded file buffer into a SQLite table."""
        df = pd.read_csv(csv_file_or_path)
        # Clean column names (strip whitespace, replace special chars with underscore)
        df.columns = [str(c).strip().replace(" ", "_").replace("-", "_").lower() for c in df.columns]

        clean_table_name = table_name.strip().replace(" ", "_").replace("-", "_").lower()
        with self._get_connection() as conn:
            df.to_sql(clean_table_name, conn, if_exists=if_exists, index=False)

        return len(df)
