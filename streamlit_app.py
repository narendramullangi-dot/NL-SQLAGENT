import json
import streamlit as st

from app.logging_config import configure_logging
from app.database.connection import check_database_connection
from app.agents.graph import run_question
from app.services.formatting import result_dataframe
from app.services.history import append_history, read_history
from app.config import ENABLE_QUERY_HISTORY

configure_logging()
st.set_page_config(page_title="NL2SQL Agent", page_icon="🧠", layout="wide")
st.title("🧠 Natural Language to SQL Agent")
st.caption("Gemini · LangGraph · SQLGlot · Neon PostgreSQL")

with st.sidebar:
    st.header("System status")
    if st.button("Test PostgreSQL connection", use_container_width=True):
        st.session_state["connection_status"] = check_database_connection()
    status = st.session_state.get("connection_status")
    if status:
        if status["ok"]:
            st.success("Database connected")
            st.caption(f"Database: {status['database_name']}")
            st.caption(f"Role: {status['database_user']}")
        else:
            st.error("Database connection failed")
            st.caption(status["error"])
    st.divider()
    st.subheader("Example questions")
    examples = [
        "How many employees are in each department?",
        "Show the top 10 employees by total claimed travel amount.",
        "Which expense items exceed their policy limits?",
        "Show total expense amount by category.",
        "How many claims were rejected by department?",
        "List claims with employee name, department, trip city and status.",
    ]
    for example in examples:
        if st.button(example, use_container_width=True):
            st.session_state["question"] = example

question = st.text_area(
    "Ask a question about your database",
    key="question",
    height=100,
    placeholder="Example: Which departments have the highest travel expenses?",
)
run = st.button("Generate SQL and execute", type="primary", disabled=not question.strip())

if run:
    with st.spinner("Understanding question → generating SQL → validating → executing..."):
        try:
            state = run_question(question)
            st.session_state["last_state"] = state
            if ENABLE_QUERY_HISTORY:
                append_history({
                    "question": question,
                    "sql": state.get("validated_sql") or state.get("generated_sql", ""),
                    "status": state.get("status", ""),
                    "row_count": (state.get("results") or {}).get("row_count", 0),
                    "execution_time_ms": state.get("execution_time_ms"),
                    "error": state.get("execution_error") or state.get("validation_error", ""),
                })
        except Exception as exc:
            st.error("Agent failed. Check application logs and configuration.")
            st.code(str(exc).splitlines()[0])
            state = None

state = st.session_state.get("last_state")
if state:
    st.divider()
    if state.get("status") == "needs_clarification":
        st.warning(state.get("clarification_question") or "Please clarify your question.")
    elif state.get("status") == "success":
        st.success("Query executed successfully")
        c1, c2, c3 = st.columns(3)
        c1.metric("Rows returned", state["results"]["row_count"])
        c2.metric("Execution time", f"{state.get('execution_time_ms', 0)} ms")
        c3.metric("SQL correction attempts", state.get("retry_count", 0))
        if state.get("explanation"):
            st.write("**Explanation:**", state["explanation"])
        with st.expander("Generated PostgreSQL SQL", expanded=True):
            st.code(state.get("validated_sql", ""), language="sql")
        df = result_dataframe(state["results"])
        st.subheader("Query results")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            "Download results as CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name="nl2sql_results.csv",
            mime="text/csv",
        )
        if state["results"].get("truncated"):
            st.info("Results were capped at the configured maximum row count.")
    else:
        st.error("The agent could not complete this query.")
        error = state.get("validation_error") or state.get("execution_error") or "Unknown error"
        st.write(error)
        if state.get("generated_sql"):
            with st.expander("Last generated SQL"):
                st.code(state["generated_sql"], language="sql")
        if state.get("retry_count") is not None:
            st.caption(f"Correction attempts: {state.get('retry_count', 0)}")

with st.expander("Recent query history"):
    history = read_history()
    if history:
        st.dataframe(history, use_container_width=True, hide_index=True)
    else:
        st.caption("No query history yet.")
