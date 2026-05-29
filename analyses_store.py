"""Armazenamento de análises (PostgreSQL).

Mantém as mesmas funções públicas e formatos de retorno da versão antiga em
JSON, para não exigir mudanças no app.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from psycopg2.extras import Json

from db import get_cursor, init_db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def list_analyses() -> list[dict[str, Any]]:
    """Retorna a lista de análises (sem o texto integral do currículo) ordenada
    da mais recente para a mais antiga."""
    init_db()
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, criado_em, arquivo, candidato_nome, resultado "
            "FROM analyses ORDER BY criado_em DESC"
        )
        rows = cur.fetchall()

    summaries: list[dict[str, Any]] = []
    for item in rows:
        resultado = item.get("resultado") or {}
        summaries.append(
            {
                "id": item["id"],
                "criado_em": item["criado_em"],
                "arquivo": item.get("arquivo", ""),
                "candidato_nome": item.get("candidato_nome", "(sem nome)"),
                "score_final": resultado.get("score_final"),
                "classificacao": resultado.get("classificacao"),
                "vaga_recomendada": (resultado.get("vaga_recomendada") or {}).get(
                    "titulo"
                ),
                "recomendacao_final": resultado.get("recomendacao_final"),
                "deteccao_ia_prob": (resultado.get("deteccao_ia") or {}).get(
                    "probabilidade"
                ),
            }
        )
    return summaries


def get_analysis(analysis_id: str) -> dict[str, Any] | None:
    init_db()
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, criado_em, arquivo, candidato_nome, curriculo_preview, "
            "resultado FROM analyses WHERE id = %s",
            (analysis_id,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def save_analysis(
    arquivo: str,
    candidato_nome: str,
    resultado: dict[str, Any],
    curriculo_preview: str,
) -> dict[str, Any]:
    init_db()
    item = {
        "id": str(uuid.uuid4()),
        "criado_em": _now(),
        "arquivo": arquivo,
        "candidato_nome": candidato_nome or "(sem nome)",
        "curriculo_preview": curriculo_preview[:4000],
        "resultado": resultado,
    }
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO analyses "
            "(id, criado_em, arquivo, candidato_nome, curriculo_preview, resultado) "
            "VALUES (%(id)s, %(criado_em)s, %(arquivo)s, %(candidato_nome)s, "
            "%(curriculo_preview)s, %(resultado)s)",
            {**item, "resultado": Json(resultado)},
        )
    return item


def delete_analysis(analysis_id: str) -> bool:
    init_db()
    with get_cursor() as cur:
        cur.execute("DELETE FROM analyses WHERE id = %s", (analysis_id,))
        return cur.rowcount > 0
