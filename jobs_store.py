"""Armazenamento de vagas (PostgreSQL).

Mantém exatamente as mesmas funções públicas e os mesmos formatos de retorno
da versão antiga em JSON, para não exigir mudanças no app.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from db import get_cursor, init_db

_COLS = "id, titulo, descricao, requisitos, criado_em"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_jobs() -> list[dict[str, Any]]:
    init_db()
    with get_cursor() as cur:
        cur.execute(f"SELECT {_COLS} FROM jobs ORDER BY criado_em ASC")
        return [dict(row) for row in cur.fetchall()]


def get_job(job_id: str) -> dict[str, Any] | None:
    init_db()
    with get_cursor() as cur:
        cur.execute(f"SELECT {_COLS} FROM jobs WHERE id = %s", (job_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def create_job(titulo: str, descricao: str, requisitos: str = "") -> dict[str, Any]:
    init_db()
    job = {
        "id": str(uuid.uuid4()),
        "titulo": titulo.strip(),
        "descricao": descricao.strip(),
        "requisitos": requisitos.strip(),
        "criado_em": _now(),
    }
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO jobs (id, titulo, descricao, requisitos, criado_em) "
            "VALUES (%(id)s, %(titulo)s, %(descricao)s, %(requisitos)s, %(criado_em)s)",
            job,
        )
    return job


def update_job(
    job_id: str,
    titulo: str | None = None,
    descricao: str | None = None,
    requisitos: str | None = None,
) -> dict[str, Any] | None:
    init_db()
    sets: list[str] = []
    params: dict[str, Any] = {"id": job_id}
    if titulo is not None:
        sets.append("titulo = %(titulo)s")
        params["titulo"] = titulo.strip()
    if descricao is not None:
        sets.append("descricao = %(descricao)s")
        params["descricao"] = descricao.strip()
    if requisitos is not None:
        sets.append("requisitos = %(requisitos)s")
        params["requisitos"] = requisitos.strip()

    with get_cursor() as cur:
        if sets:
            cur.execute(
                f"UPDATE jobs SET {', '.join(sets)} WHERE id = %(id)s "
                f"RETURNING {_COLS}",
                params,
            )
            row = cur.fetchone()
        else:
            cur.execute(f"SELECT {_COLS} FROM jobs WHERE id = %(id)s", params)
            row = cur.fetchone()
        return dict(row) if row else None


def delete_job(job_id: str) -> bool:
    init_db()
    with get_cursor() as cur:
        cur.execute("DELETE FROM jobs WHERE id = %s", (job_id,))
        return cur.rowcount > 0
