
import json
import logging

from google import genai
from google.genai import types, errors

from app.config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger(__name__)

# Explicitly use v1beta for JSON structured output.
client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(
        api_version="v1beta"
    )
)


def generate_sql(
    question: str,
    schema_context: str,
    previous_sql: str = "",
    execution_error: str = ""
) -> dict:

    system_rules = """
You are a careful PostgreSQL text-to-SQL engine.
Generate one read-only SELECT query.

Rules:
- Use ONLY tables and columns present in the supplied schema.
- Use PostgreSQL syntax.
- Never generate INSERT, UPDATE, DELETE, MERGE, CREATE, ALTER,
  DROP, TRUNCATE, COPY, CALL, DO, GRANT, REVOKE,
  transaction commands, or multiple statements.
- Never use SELECT INTO or row-locking clauses.
- Do not access system catalogs or other schemas.
- Prefer explicit column names; do not use SELECT *.
- Use declared foreign keys for joins.
- Do not invent business values or filters.
- If the question is ambiguous, ask one concise clarification question.
- Return JSON only.
"""

    prompt = f"""
{system_rules}

DATABASE SCHEMA:
{schema_context}

USER QUESTION:
{question}

PREVIOUS SQL (if correcting):
{previous_sql or "None"}

DATABASE ERROR (if correcting):
{execution_error or "None"}

Return JSON with:
sql: string (empty if clarification is required)
explanation: short string
needs_clarification: boolean
clarification_question: string
"""

    try:
        logger.info("Calling Gemini model: %s", GEMINI_MODEL)

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema={
                    "type": "OBJECT",
                    "properties": {
                        "sql": {"type": "STRING"},
                        "explanation": {"type": "STRING"},
                        "needs_clarification": {"type": "BOOLEAN"},
                        "clarification_question": {"type": "STRING"},
                    },
                    "required": [
                        "sql",
                        "explanation",
                        "needs_clarification",
                        "clarification_question",
                    ],
                },
                temperature=0.1,
            ),
        )

        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")

        result = json.loads(response.text)

        logger.info("Gemini SQL generation successful")

        return result

    except errors.APIError as exc:
        logger.exception(
            "Gemini API error: HTTP %s - %s",
            exc.code,
            exc.message
        )
        raise

    except json.JSONDecodeError:
        logger.exception("Gemini returned invalid JSON")
        raise

    except Exception:
        logger.exception("Unexpected Gemini generation error")
        raise
