"""Cliente mínimo da API do monday.com (GraphQL).

Usado pela triagem automática SEM n8n: o portal recebe o webhook do Monday,
lê o currículo anexado no item e escreve a etiqueta de avaliação de volta.

Requer a variável de ambiente ``MONDAY_API_TOKEN`` (token de API de uma conta
com acesso ao board de Recrutamento).
"""
from __future__ import annotations

import json
import os
from typing import Any

import requests

MONDAY_API = "https://api.monday.com/v2"

# Títulos das colunas no board (case-insensitive, "contém"). Ajuste aqui se o
# RH renomear as colunas.
STATUS_COL_TITLES = ("avaliação de currículo", "avaliacao de curriculo")
FILE_COL_TITLES = ("anexe seu currículo", "anexe seu curriculo", "currículo", "curriculo")


class MondayError(RuntimeError):
    pass


def _token() -> str:
    token = os.environ.get("MONDAY_API_TOKEN", "").strip()
    if not token:
        raise MondayError("MONDAY_API_TOKEN não configurada no servidor.")
    return token


def _gql(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    resp = requests.post(
        MONDAY_API,
        json={"query": query, "variables": variables or {}},
        headers={
            "Authorization": _token(),
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    try:
        body = resp.json()
    except ValueError as exc:  # noqa: BLE001
        raise MondayError(f"Resposta inválida do Monday (HTTP {resp.status_code}).") from exc
    if resp.status_code >= 400 or body.get("errors"):
        msg = body.get("errors") or body.get("error_message") or resp.text[:300]
        raise MondayError(f"Erro na API do Monday: {msg}")
    return body.get("data") or {}


def _match_col(columns: list[dict[str, Any]], titles: tuple[str, ...],
               col_type: str | None = None) -> dict[str, Any] | None:
    for col in columns:
        title = (col.get("title") or "").strip().lower()
        if col_type and col.get("type") != col_type:
            continue
        if any(t in title for t in titles):
            return col
    return None


def get_item_context(item_id: str | int) -> dict[str, Any]:
    """Lê o item: nome, IDs das colunas (status/arquivo), etiqueta atual e a
    URL pública (temporária) do currículo anexado."""
    data = _gql(
        """
        query ($ids: [ID!]!) {
          items (ids: $ids) {
            id
            name
            board { id columns { id title type } }
            column_values { id text value }
          }
        }
        """,
        {"ids": [str(item_id)]},
    )
    items = data.get("items") or []
    if not items:
        raise MondayError(f"Item {item_id} não encontrado.")
    item = items[0]
    board = item.get("board") or {}
    columns = board.get("columns") or []
    col_values = {cv["id"]: cv for cv in (item.get("column_values") or [])}

    status_col = _match_col(columns, STATUS_COL_TITLES, col_type="status")
    file_col = _match_col(columns, FILE_COL_TITLES, col_type="file")
    if not status_col:
        raise MondayError("Coluna de status 'Avaliação de Currículo' não encontrada.")
    if not file_col:
        raise MondayError("Coluna de arquivo 'Anexe seu currículo' não encontrada.")

    status_now = (col_values.get(status_col["id"], {}) or {}).get("text") or ""

    # assetIds do currículo anexado
    file_raw = (col_values.get(file_col["id"], {}) or {}).get("value")
    asset_ids: list[str] = []
    if file_raw:
        try:
            parsed = json.loads(file_raw)
            for f in parsed.get("files", []):
                aid = f.get("assetId") or f.get("asset_id")
                if aid:
                    asset_ids.append(str(aid))
        except (ValueError, AttributeError):
            pass

    cv_url = None
    cv_name = None
    if asset_ids:
        assets = _gql(
            "query ($aids: [ID!]!) { assets (ids: $aids) { id name public_url } }",
            {"aids": asset_ids},
        ).get("assets") or []
        if assets:
            cv_url = assets[0].get("public_url")
            cv_name = assets[0].get("name")

    return {
        "item_id": str(item.get("id")),
        "board_id": str(board.get("id")),
        "name": item.get("name"),
        "status_column_id": status_col["id"],
        "status_atual": status_now,
        "cv_url": cv_url,
        "cv_name": cv_name,
    }


def set_status(board_id: str | int, item_id: str | int,
               column_id: str, label: str) -> None:
    """Define a etiqueta (label) de uma coluna de status pelo texto."""
    _gql(
        """
        mutation ($bid: ID!, $iid: ID!, $cid: String!, $val: String!) {
          change_simple_column_value (board_id: $bid, item_id: $iid,
              column_id: $cid, value: $val) { id }
        }
        """,
        {
            "bid": str(board_id),
            "iid": str(item_id),
            "cid": column_id,
            "val": label,
        },
    )
