"""Armazenamento de análises (PostgreSQL).

Mantém as mesmas funções públicas e formatos de retorno da versão antiga em
JSON, para não exigir mudanças no app.py.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from psycopg2 import Binary
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
            "SELECT id, criado_em, arquivo, candidato_nome, resultado, "
            "(arquivo_bytes IS NOT NULL) AS tem_arquivo "
            "FROM analyses ORDER BY criado_em DESC"
        )
        rows = cur.fetchall()

    summaries: list[dict[str, Any]] = []
    for item in rows:
        resultado = item.get("resultado") or {}
        pcd = resultado.get("analise_pcd") or {}
        summaries.append(
            {
                "id": item["id"],
                "criado_em": item["criado_em"],
                "arquivo": item.get("arquivo", ""),
                "candidato_nome": item.get("candidato_nome", "(sem nome)"),
                "tem_arquivo": bool(item.get("tem_arquivo")),
                "score_final": resultado.get("score_final"),
                "classificacao": resultado.get("classificacao"),
                "vaga_recomendada": (resultado.get("vaga_recomendada") or {}).get(
                    "titulo"
                ),
                "recomendacao_final": resultado.get("recomendacao_final"),
                "deteccao_ia_prob": (resultado.get("deteccao_ia") or {}).get(
                    "probabilidade"
                ),
                # Resumo PCD para o filtro do histórico (sem expor a condição/CID).
                "pcd": {
                    "is_pcd": bool(pcd.get("is_pcd")),
                    "indicador": pcd.get("indicador"),
                    "titulo": pcd.get("titulo"),
                },
            }
        )
    return summaries


def get_analysis(analysis_id: str) -> dict[str, Any] | None:
    """Análise completa para a tela — sem o conteúdo binário do arquivo."""
    init_db()
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, criado_em, arquivo, candidato_nome, curriculo_preview, "
            "resultado, arquivo_mime, arquivo_tamanho, "
            "(arquivo_bytes IS NOT NULL) AS tem_arquivo "
            "FROM analyses WHERE id = %s",
            (analysis_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        item = dict(row)
        item["tem_arquivo"] = bool(item.get("tem_arquivo"))
        return item


def get_analysis_file(analysis_id: str) -> dict[str, Any] | None:
    """Currículo original guardado junto da análise (para abrir/baixar).

    Devolve ``None`` se a análise não existir; ``arquivo_bytes`` vem ``None``
    quando o arquivo não foi guardado (análises feitas antes desta versão).
    """
    init_db()
    with get_cursor() as cur:
        cur.execute(
            "SELECT arquivo, candidato_nome, arquivo_mime, arquivo_bytes "
            "FROM analyses WHERE id = %s",
            (analysis_id,),
        )
        row = cur.fetchone()
        if not row:
            return None
        raw = row.get("arquivo_bytes")
        return {
            "arquivo": row.get("arquivo") or "curriculo",
            "candidato_nome": row.get("candidato_nome") or "(sem nome)",
            "arquivo_mime": row.get("arquivo_mime") or "",
            # psycopg2 devolve BYTEA como memoryview.
            "arquivo_bytes": bytes(raw) if raw is not None else None,
        }


def save_analysis(
    arquivo: str,
    candidato_nome: str,
    resultado: dict[str, Any],
    curriculo_preview: str,
    arquivo_bytes: bytes | None = None,
    arquivo_mime: str = "",
) -> dict[str, Any]:
    init_db()
    item = {
        "id": str(uuid.uuid4()),
        "criado_em": _now(),
        "arquivo": arquivo,
        "candidato_nome": candidato_nome or "(sem nome)",
        "curriculo_preview": curriculo_preview[:4000],
        "resultado": resultado,
        "arquivo_mime": arquivo_mime or "",
        "arquivo_tamanho": len(arquivo_bytes or b""),
        "tem_arquivo": arquivo_bytes is not None,
    }
    with get_cursor() as cur:
        cur.execute(
            "INSERT INTO analyses "
            "(id, criado_em, arquivo, candidato_nome, curriculo_preview, resultado, "
            "arquivo_mime, arquivo_tamanho, arquivo_bytes) "
            "VALUES (%(id)s, %(criado_em)s, %(arquivo)s, %(candidato_nome)s, "
            "%(curriculo_preview)s, %(resultado)s, %(arquivo_mime)s, "
            "%(arquivo_tamanho)s, %(arquivo_bytes)s)",
            {
                **item,
                "resultado": Json(resultado),
                "arquivo_bytes": Binary(arquivo_bytes) if arquivo_bytes else None,
            },
        )
    return item


def delete_analysis(analysis_id: str) -> bool:
    init_db()
    with get_cursor() as cur:
        cur.execute("DELETE FROM analyses WHERE id = %s", (analysis_id,))
        return cur.rowcount > 0
