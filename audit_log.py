"""Log de auditoria do portal — registra criação/edição/exclusão de vagas,
análises de currículo (sucesso e falha) e exceções inesperadas."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

DATA_DIR = Path(__file__).parent / "data"
AUDIT_FILE = DATA_DIR / "audit.json"
MAX_EVENTS = 500  # mantém só os últimos N eventos para a UI

EventLevel = Literal["info", "warn", "error"]
EventCategory = Literal["vaga", "analise", "sistema"]

_lock = threading.Lock()


def _ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not AUDIT_FILE.exists():
        AUDIT_FILE.write_text("[]", encoding="utf-8")


def _read_all() -> list[dict[str, Any]]:
    _ensure_storage()
    raw = AUDIT_FILE.read_text(encoding="utf-8") or "[]"
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _write_all(items: list[dict[str, Any]]) -> None:
    _ensure_storage()
    AUDIT_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def log(
    category: EventCategory,
    action: str,
    message: str,
    level: EventLevel = "info",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = {
        "id": str(uuid.uuid4()),
        "criado_em": datetime.now(timezone.utc).isoformat(),
        "category": category,
        "action": action,
        "level": level,
        "message": message,
        "meta": meta or {},
    }
    with _lock:
        items = _read_all()
        items.append(event)
        if len(items) > MAX_EVENTS:
            items = items[-MAX_EVENTS:]
        _write_all(items)
    return event


def list_events(
    limit: int = 200,
    category: EventCategory | None = None,
    level: EventLevel | None = None,
) -> list[dict[str, Any]]:
    with _lock:
        items = _read_all()
    if category:
        items = [i for i in items if i.get("category") == category]
    if level:
        items = [i for i in items if i.get("level") == level]
    items.sort(key=lambda x: x.get("criado_em", ""), reverse=True)
    return items[:limit]


def clear_events() -> int:
    with _lock:
        items = _read_all()
        count = len(items)
        _write_all([])
    return count
