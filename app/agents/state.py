from typing import TypedDict, Any

class NL2SQLState(TypedDict, total=False):
    question: str
    schema_metadata: dict
    schema_context: str
    generated_sql: str
    validated_sql: str
    explanation: str
    needs_clarification: bool
    clarification_question: str
    validation_error: str
    execution_error: str
    results: dict[str, Any]
    retry_count: int
    status: str
