"""Armazenamento de análises em JSON local."""
from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).parent / "data"
ANALYSES_FILE = DATA_DIR / "analyses.json"

_lock = threading.Lock()


def _ensure_storage() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not ANALYSES_FILE.exists():
        ANALYSES_FILE.write_text("[]", encoding="utf-8")


def _read_all() -> list[dict[str, Any]]:
    _ensure_storage()
    raw = ANALYSES_FILE.read_text(encoding="utf-8") or "[]"
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _write_all(items: list[dict[str, Any]]) -> None:
    _ensure_storage()
    ANALYSES_FILE.write_text(
        json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def list_analyses() -> list[dict[str, Any]]:
    """Retorna a lista de análises (sem o texto integral do currículo) ordenada
    da mais recente para a mais antiga."""
    with _lock:
        items = _read_all()
    summaries = [
        {
            "id": item["id"],
            "criado_em": item["criado_em"],
            "arquivo": item.get("arquivo", ""),
            "candidato_nome": item.get("candidato_nome", "(sem nome)"),
            "score_final": item.get("resultado", {}).get("score_final"),
            "classificacao": item.get("resultado", {}).get("classificacao"),
            "vaga_recomendada": (
                item.get("resultado", {}).get("vaga_recomendada", {}) or {}
            ).get("titulo"),
            "recomendacao_final": item.get("resultado", {}).get("recomendacao_final"),
            "deteccao_ia_prob": (
                item.get("resultado", {}).get("deteccao_ia", {}) or {}
            ).get("probabilidade"),
        }
        for item in items
    ]
    summaries.sort(key=lambda x: x["criado_em"], reverse=True)
    return summaries


def get_analysis(analysis_id: str) -> dict[str, Any] | None:
    with _lock:
        for item in _read_all():
            if item["id"] == analysis_id:
                return item
    return None


def save_analysis(
    arquivo: str,
    candidato_nome: str,
    resultado: dict[str, Any],
    curriculo_preview: str,
) -> dict[str, Any]:
    item = {
        "id": str(uuid.uuid4()),
        "criado_em": datetime.now(timezone.utc).isoformat(),
        "arquivo": arquivo,
        "candidato_nome": candidato_nome or "(sem nome)",
        "curriculo_preview": curriculo_preview[:4000],
        "resultado": resultado,
    }
    with _lock:
        items = _read_all()
        items.append(item)
        _write_all(items)
    return item


def delete_analysis(analysis_id: str) -> bool:
    with _lock:
        items = _read_all()
        new_items = [i for i in items if i["id"] != analysis_id]
        if len(new_items) == len(items):
            return False
        _write_all(new_items)
        return True
