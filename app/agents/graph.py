import time
from langgraph.graph import StateGraph, END
from app.agents.state import NL2SQLState
from app.config import DB_SCHEMA, DB_MAX_ROWS, MAX_SQL_RETRIES
from app.database.connection import engine
from app.database.schema_loader import load_schema, schema_to_prompt_context
from app.llm.gemini_client import generate_sql
from app.sql.validator import validate_and_normalize_sql
from app.database.executor import execute_read_only

def schema_node(state: NL2SQLState) -> dict:
    metadata = load_schema(engine, DB_SCHEMA)
    return {
        "schema_metadata": metadata,
        "schema_context": schema_to_prompt_context(metadata),
        "status": "schema_loaded",
    }

def generate_node(state: NL2SQLState) -> dict:
    generated = generate_sql(
        question=state["question"],
        schema_context=state["schema_context"],
        previous_sql=state.get("generated_sql", ""),
        execution_error=state.get("validation_error") or state.get("execution_error", ""),
    )
    if generated.get("needs_clarification"):
        return {
            "needs_clarification": True,
            "clarification_question": generated.get("clarification_question", ""),
            "explanation": generated.get("explanation", ""),
            "status": "needs_clarification",
        }
    return {
        "generated_sql": generated.get("sql", ""),
        "explanation": generated.get("explanation", ""),
        "needs_clarification": False,
        "validation_error": "",
        "execution_error": "",
        "status": "generated",
    }

def validate_node(state: NL2SQLState) -> dict:
    result = validate_and_normalize_sql(
        state.get("generated_sql", ""),
        state["schema_metadata"],
        DB_SCHEMA,
        DB_MAX_ROWS,
    )
    if not result.valid:
        return {
            "validation_error": result.error,
            "retry_count": state.get("retry_count", 0) + 1,
            "status": "validation_failed",
        }
    return {
        "validated_sql": result.sql,
        "validation_error": "",
        "status": "validated",
    }

def execute_node(state: NL2SQLState) -> dict:
    started = time.perf_counter()
    result = execute_read_only(state["validated_sql"])
    elapsed = round((time.perf_counter() - started) * 1000, 2)
    if not result["ok"]:
        return {
            "execution_error": result["error"],
            "retry_count": state.get("retry_count", 0) + 1,
            "execution_time_ms": elapsed,
            "status": "execution_failed",
        }
    return {
        "results": result,
        "execution_time_ms": elapsed,
        "execution_error": "",
        "status": "success",
    }

def route_after_generate(state: NL2SQLState) -> str:
    if state.get("needs_clarification"):
        return "end"
    if not state.get("generated_sql"):
        return "end"
    return "validate"

def route_after_validation(state: NL2SQLState) -> str:
    if state.get("status") == "validated":
        return "execute"
    if state.get("retry_count", 0) <= MAX_SQL_RETRIES:
        return "generate"
    return "end"

def route_after_execution(state: NL2SQLState) -> str:
    if state.get("status") == "success":
        return "end"
    if state.get("retry_count", 0) <= MAX_SQL_RETRIES:
        return "generate"
    return "end"

def build_graph():
    graph = StateGraph(NL2SQLState)
    graph.add_node("schema", schema_node)
    graph.add_node("generate", generate_node)
    graph.add_node("validate", validate_node)
    graph.add_node("execute", execute_node)

    graph.set_entry_point("schema")
    graph.add_edge("schema", "generate")
    graph.add_conditional_edges("generate", route_after_generate, {
        "validate": "validate",
        "end": END,
    })
    graph.add_conditional_edges("validate", route_after_validation, {
        "execute": "execute",
        "generate": "generate",
        "end": END,
    })
    graph.add_conditional_edges("execute", route_after_execution, {
        "generate": "generate",
        "end": END,
    })
    return graph.compile()

nl2sql_graph = build_graph()

def run_question(question: str) -> dict:
    initial: NL2SQLState = {
        "question": question.strip(),
        "retry_count": 0,
        "status": "started",
    }
    return nl2sql_graph.invoke(initial)
