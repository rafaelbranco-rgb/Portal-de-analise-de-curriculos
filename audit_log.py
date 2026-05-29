"""Log de auditoria do portal — registra criação/edição/exclusão de vagas,
análises de currículo (sucesso e falha) e exceções inesperadas.

Armazenamento em PostgreSQL. Mantém as mesmas funções públicas e formatos de
retorno da versão antiga em JSON.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from psycopg2.extras import Json

from db import get_cursor, init_db

MAX_EVENTS = 500  # mantém só os últimos N eventos para a UI

EventLevel = Literal["info", "warn", "error"]
EventCategory = Literal["vaga", "analise", "sistema"]

_COLS = "id, criado_em, category, action, level, message, meta"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(
    category: EventCategory,
    action: str,
    message: str,
    level: EventLevel = "info",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    init_db()
    event = {
        "id": str(uuid.uuid4()),
        "criado_em": _now(),
        "category": category,
        "action": action,
        "level": level,
        "message": message,
        "meta": meta or {},
    }
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO audit_events "
            "(id, criado_em, category, action, level, message, meta) "
            "VALUES (%(id)s, %(criado_em)s, %(category)s, %(action)s, "
            "%(level)s, %(message)s, %(meta)s)",
            {**event, "meta": Json(event["meta"])},
        )
        # Mantém apenas os MAX_EVENTS eventos mais recentes.
        cur.execute(
            "DELETE FROM audit_events WHERE id NOT IN ("
            "SELECT id FROM audit_events ORDER BY criado_em DESC LIMIT %s)",
            (MAX_EVENTS,),
        )
    return event


def list_events(
    limit: int = 200,
    category: EventCategory | None = None,
    level: EventLevel | None = None,
) -> list[dict[str, Any]]:
    init_db()
    clauses: list[str] = []
    params: list[Any] = []
    if category:
        clauses.append("category = %s")
        params.append(category)
    if level:
        clauses.append("level = %s")
        params.append(level)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)
    with get_cursor() as cur:
        cur.execute(
            f"SELECT {_COLS} FROM audit_events{where} "
            f"ORDER BY criado_em DESC LIMIT %s",
            params,
        )
        return [dict(row) for row in cur.fetchall()]


def clear_events() -> int:
    init_db()
    with get_cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM audit_events")
        count = int(cur.fetchone()["c"])
        cur.execute("DELETE FROM audit_events")
    return count
