import json
from datetime import datetime, timezone
from pathlib import Path

HISTORY_FILE = Path("query_history.jsonl")

def append_history(entry: dict):
    safe = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "question": entry.get("question", ""),
        "sql": entry.get("sql", ""),
        "status": entry.get("status", ""),
        "row_count": entry.get("row_count", 0),
        "execution_time_ms": entry.get("execution_time_ms"),
        "error": entry.get("error", ""),
    }
    with HISTORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(safe, default=str) + "\n")

def read_history(limit: int = 50) -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    lines = HISTORY_FILE.read_text(encoding="utf-8").splitlines()[-limit:]
    output = []
    for line in reversed(lines):
        try:
            output.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return output
