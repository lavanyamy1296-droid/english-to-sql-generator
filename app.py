"""Plain English to SQL Generator - Streamlit Web Application."""

import os
import sys
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.config import (
    DEFAULT_DB_PATH,
    DEFAULT_PROVIDER,
    EXECUTION_TIMEOUT_SECONDS,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GROQ_API_KEY,
    GROQ_MODEL,
    MAX_RESULT_ROWS,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    READ_ONLY_MODE,
    TEMPERATURE,
)
from src.database.db_manager import DatabaseManager
from src.database.sample_data import create_sample_database
from src.llm.guardrails import format_sql, validate_sql_query
from src.llm.self_healing import heal_sql_query
from src.llm.sql_generator import SQLGenerator

# Page configuration
st.set_page_config(
    page_title="SQLCraft | Plain English to SQL Generator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for a modern, sleek interface
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #3B82F6, #8B5CF6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #6B7280;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
    .stButton>button {
        border-radius: 6px;
        font-weight: 600;
    }
    .sql-card {
        border-left: 4px solid #3B82F6;
        padding-left: 12px;
        margin-top: 8px;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Initialize Session State
if "history" not in st.session_state:
    st.session_state.history = []
if "current_sql" not in st.session_state:
    st.session_state.current_sql = ""
if "current_explanation" not in st.session_state:
    st.session_state.current_explanation = ""
if "current_query_text" not in st.session_state:
    st.session_state.current_query_text = ""
if "execution_result" not in st.session_state:
    st.session_state.execution_result = None
if "healing_note" not in st.session_state:
    st.session_state.healing_note = None

# Ensure default demo database exists
create_sample_database(DEFAULT_DB_PATH)

# ==========================================
# SIDEBAR: Database & Model Settings
# ==========================================
with st.sidebar:
    st.markdown("### 🗄️ Database Source")
    db_source_option = st.radio(
        "Choose Database:",
        ["Enterprise Demo (eCommerce & HR)", "Upload Custom SQLite (.db/.sqlite)", "Upload CSV to Query"],
        index=0,
    )

    db_path = DEFAULT_DB_PATH

    if db_source_option == "Enterprise Demo (eCommerce & HR)":
        db_path = DEFAULT_DB_PATH
        st.success("Connected to Enterprise Demo DB")

    elif db_source_option == "Upload Custom SQLite (.db/.sqlite)":
        uploaded_db = st.file_uploader("Upload .db or .sqlite", type=["db", "sqlite", "sqlite3"])
        if uploaded_db:
            upload_dir = Path("data/uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)
            saved_path = upload_dir / uploaded_db.name
            with open(saved_path, "wb") as f:
                f.write(uploaded_db.getbuffer())
            db_path = saved_path
            st.success(f"Loaded: `{uploaded_db.name}`")
        else:
            st.info("Using demo database until file uploaded.")

    elif db_source_option == "Upload CSV to Query":
        uploaded_csv = st.file_uploader("Upload CSV file", type=["csv"])
        if uploaded_csv:
            upload_dir = Path("data/uploads")
            upload_dir.mkdir(parents=True, exist_ok=True)
            csv_db_path = upload_dir / "csv_database.db"
            db_manager_temp = DatabaseManager(csv_db_path)
            table_name = Path(uploaded_csv.name).stem.replace(" ", "_").lower()
            row_count = db_manager_temp.import_csv_to_table(uploaded_csv, table_name)
            db_path = csv_db_path
            st.success(f"Imported `{uploaded_csv.name}` into table `{table_name}` ({row_count} rows)")
        else:
            st.info("Upload a CSV file to query it.")

    # Initialize DB Manager
    db_manager = DatabaseManager(db_path)
    tables = db_manager.get_tables()

    # Schema Explorer
    st.markdown("---")
    st.markdown("### 🔍 Schema Explorer")
    if tables:
        selected_table = st.selectbox("Inspect Table:", tables)
        if selected_table:
            schema_meta = db_manager.get_table_schema(selected_table)
            st.caption(f"**Rows:** {schema_meta['row_count']}")
            cols_df = pd.DataFrame(schema_meta["columns"])[["name", "type", "is_pk"]]
            cols_df.columns = ["Column", "Type", "Primary Key"]
            st.dataframe(cols_df, hide_index=True, use_container_width=True)

            if schema_meta["foreign_keys"]:
                st.caption("**Foreign Keys:**")
                for fk in schema_meta["foreign_keys"]:
                    st.text(f"• {fk['from_col']} ➔ {fk['to_table']}({fk['to_col']})")
    else:
        st.warning("No tables detected.")

    # LLM Settings
    st.markdown("---")
    st.markdown("### ⚙️ LLM Configuration")
    provider = st.selectbox(
        "Provider:",
        ["groq", "gemini", "openai"],
        index=0 if DEFAULT_PROVIDER == "groq" else (1 if DEFAULT_PROVIDER == "gemini" else 2),
    )

    if provider == "groq":
        api_key = st.text_input("Groq API Key", value=GROQ_API_KEY, type="password")
        model = st.selectbox("Groq Model", ["openai/gpt-oss-120b", "openai/gpt-oss-20b", "qwen/qwen3.8-27b"], index=0)
    elif provider == "gemini":
        api_key = st.text_input("Gemini API Key", value=GEMINI_API_KEY, type="password")
        model = st.selectbox("Gemini Model", ["gemini-1.5-flash", "gemini-2.0-flash-exp", "gemini-1.5-pro"], index=0)
    else:
        api_key = st.text_input("OpenAI API Key", value=OPENAI_API_KEY, type="password")
        model = st.selectbox("OpenAI Model", ["gpt-4o-mini", "gpt-4o"], index=0)

    temperature = st.slider("Temperature", min_value=0.0, max_value=1.0, value=TEMPERATURE, step=0.05)
    read_only = st.checkbox("Read-Only Guardrail (Block DROP/DELETE)", value=READ_ONLY_MODE)

# ==========================================
# MAIN CONTENT: Header & Query Generator
# ==========================================
st.markdown('<div class="main-title">⚡ Plain English to SQL Generator</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Ask questions in everyday English, instantly generate optimized SQL, inspect execution results, and view auto-charts.</div>',
    unsafe_allow_html=True,
)

# Sample Query Chips (Quick Launchers)
st.markdown("**💡 Quick Examples:**")
col_s1, col_s2, col_s3, col_s4 = st.columns(4)

sample_prompt = None
with col_s1:
    if st.button("🏆 Top 3 Customers by Spending"):
        sample_prompt = "What are the top 3 highest spending customers with their total spent?"
with col_s2:
    if st.button("🏢 Department Avg Salaries"):
        sample_prompt = "List all departments with their average employee salary ordered from highest to lowest"
with col_s3:
    if st.button("📦 Low Stock Products (<35)"):
        sample_prompt = "Show products with stock quantity less than 35 and unit price greater than 100"
with col_s4:
    if st.button("📈 Order Status Breakdown"):
        sample_prompt = "Count the number of orders and total revenue for each order status"

# Input Box
default_input = sample_prompt if sample_prompt else st.session_state.current_query_text
user_query = st.text_area(
    "Type your question in Plain English:",
    value=default_input,
    height=85,
    placeholder="e.g. Which department has the most employees and what is the total salary?",
)

col_btn1, col_btn2 = st.columns([1, 5])
with col_btn1:
    generate_clicked = st.button("🚀 Generate SQL", type="primary", use_container_width=True)
with col_btn2:
    if st.session_state.current_sql and st.button("🔄 Re-Run Current SQL", use_container_width=False):
        generate_clicked = False
        re_run_clicked = True
    else:
        re_run_clicked = False

# Action: Generate SQL
if generate_clicked:
    if not user_query.strip():
        st.warning("Please enter a question to generate SQL.")
    else:
        st.session_state.current_query_text = user_query
        st.session_state.healing_note = None

        with st.spinner(f"Consulting {provider} ({model}) and analyzing schema..."):
            try:
                schema_context = db_manager.get_formatted_schema_for_llm()
                generator = SQLGenerator(
                    provider=provider,
                    api_key=api_key,
                    model=model,
                    temperature=temperature,
                )
                response = generator.generate_sql(user_query, schema_context)

                st.session_state.current_sql = response["sql"]
                st.session_state.current_explanation = response["explanation"]

                # Automatically validate and execute
                is_safe, guard_err = validate_sql_query(response["sql"], read_only=read_only)
                if not is_safe:
                    st.session_state.execution_result = {
                        "success": False,
                        "error": guard_err,
                        "df": pd.DataFrame(),
                        "time_ms": 0.0,
                    }
                else:
                    q_res = db_manager.execute_query(
                        response["sql"],
                        max_rows=MAX_RESULT_ROWS,
                        timeout_seconds=EXECUTION_TIMEOUT_SECONDS,
                    )

                    # If query failed with a syntax/schema error, invoke Self-Healing!
                    if not q_res.success:
                        st.info("⚠️ Query encountered an error. Engaging Self-Healing Agent to diagnose and fix...")
                        healed = heal_sql_query(
                            failed_sql=response["sql"],
                            error_message=q_res.error or "Unknown error",
                            schema_context=schema_context,
                            natural_language_query=user_query,
                            generator=generator,
                        )
                        st.session_state.healing_note = {
                            "original_error": q_res.error,
                            "diagnosis": healed.get("error_cause", "Automatic correction applied"),
                            "fixed_explanation": healed.get("explanation", ""),
                        }
                        st.session_state.current_sql = healed["sql"]
                        q_res = db_manager.execute_query(healed["sql"], max_rows=MAX_RESULT_ROWS)

                    st.session_state.execution_result = {
                        "success": q_res.success,
                        "error": q_res.error,
                        "df": q_res.to_dataframe(),
                        "time_ms": q_res.execution_time_ms,
                    }

                # Save to history
                st.session_state.history.insert(
                    0,
                    {
                        "query": user_query,
                        "sql": st.session_state.current_sql,
                        "success": st.session_state.execution_result["success"],
                    },
                )

            except Exception as e:
                st.error(f"Error generating SQL: {str(e)}")

# ==========================================
# DISPLAY: Generated SQL & Explanations
# ==========================================
if st.session_state.current_sql:
    st.markdown("---")

    # Healing notification banner if self-healing was used
    if st.session_state.healing_note:
        st.warning(
            f"🩹 **Self-Healing Agent Auto-Repaired Query:**\n\n"
            f"- **Issue Diagnosed:** {st.session_state.healing_note['diagnosis']}\n"
            f"- **Fix Applied:** {st.session_state.healing_note['fixed_explanation']}"
        )

    col_sql_header, col_copy = st.columns([4, 1])
    with col_sql_header:
        st.markdown("### 📝 Generated SQL Query")
    with col_copy:
        st.code(st.session_state.current_sql, language="sql")

    # SQL Editor (Allow users to edit and re-run)
    edited_sql = st.text_area(
        "Edit SQL Query if needed:",
        value=st.session_state.current_sql,
        height=120,
        key="sql_editor_area",
    )

    col_action1, col_action2 = st.columns([1, 4])
    with col_action1:
        if st.button("▶️ Execute Query", type="secondary"):
            is_safe, guard_err = validate_sql_query(edited_sql, read_only=read_only)
            if not is_safe:
                st.error(guard_err)
            else:
                q_res = db_manager.execute_query(edited_sql, max_rows=MAX_RESULT_ROWS)
                st.session_state.execution_result = {
                    "success": q_res.success,
                    "error": q_res.error,
                    "df": q_res.to_dataframe(),
                    "time_ms": q_res.execution_time_ms,
                }
                st.session_state.current_sql = edited_sql

    with col_action2:
        if st.session_state.current_explanation:
            st.info(f"💡 **AI Explanation:** {st.session_state.current_explanation}")

    # ==========================================
    # DISPLAY: Execution Results & Visualizations
    # ==========================================
    if st.session_state.execution_result:
        res = st.session_state.execution_result
        st.markdown("### 📊 Query Execution Results")

        if not res["success"]:
            st.error(f"❌ Execution Error: {res['error']}")
        else:
            df = res["df"]
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Rows Returned", len(df))
            with m2:
                st.metric("Execution Time", f"{res['time_ms']} ms")
            with m3:
                st.metric("Status", "Success ✅")

            if not df.empty:
                st.dataframe(df, use_container_width=True)

                # Export CSV button
                csv_bytes = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="📥 Export Results as CSV",
                    data=csv_bytes,
                    file_name="query_results.csv",
                    mime="text/csv",
                )

                # Automatic Plotly Chart Generation if suitable
                numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
                text_cols = df.select_dtypes(include=["object", "string"]).columns.tolist()

                if len(numeric_cols) >= 1 and len(text_cols) >= 1 and len(df) <= 50:
                    with st.expander("📈 Visual Chart", expanded=True):
                        x_col = text_cols[0]
                        y_col = numeric_cols[0]
                        fig = px.bar(
                            df,
                            x=x_col,
                            y=y_col,
                            title=f"{y_col} by {x_col}",
                            color=y_col,
                            color_continuous_scale="Blues",
                        )
                        fig.update_layout(xaxis_title=x_col, yaxis_title=y_col)
                        st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Query returned 0 rows.")

# ==========================================
# QUERY HISTORY
# ==========================================
if st.session_state.history:
    with st.expander("📜 Recent Query History", expanded=False):
        for idx, item in enumerate(st.session_state.history[:10]):
            status_icon = "✅" if item["success"] else "❌"
            st.markdown(f"**{idx + 1}. {status_icon} {item['query']}**")
            st.code(item["sql"], language="sql")
