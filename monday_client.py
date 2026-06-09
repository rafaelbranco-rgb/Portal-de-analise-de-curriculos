"""Cliente mínimo da API do monday.com (GraphQL).

Usado pela triagem automática SEM n8n: o portal recebe o webhook do Monday,
lê o currículo anexado no item e escreve a etiqueta de avaliação de volta.

Requer a variável de ambiente ``MONDAY_API_TOKEN`` (token de API de uma conta
com acesso ao board de Recrutamento).
"""
from __future__ import annotations

import json
import os
import unicodedata
from typing import Any

import requests

MONDAY_API = "https://api.monday.com/v2"

# Títulos das colunas no board (case-insensitive, "contém"). Ajuste aqui se o
# RH renomear as colunas.
STATUS_COL_TITLES = ("avaliação de currículo", "avaliacao de curriculo")
FILE_COL_TITLES = ("anexe seu currículo", "anexe seu curriculo", "currículo", "curriculo")
# Colunas novas do formulário relacionadas a PCD (Pessoa com Deficiência).
PCD_COL_TITLES = ("pcd",)
PCD_ESPEC_COL_TITLES = ("especifica",)   # "Especificação:"
LAUDO_COL_TITLES = ("laudo",)            # "Laudo Atualizado" (coluna de arquivo)

# Mapa Departamento (rótulo no recrutamento) -> board de Captação do setor.
# Setores sem board (Geral, CGI, Recepção, Supervisão, Portaria, Marketing) ficam
# de fora de propósito (RH trata manual). Chaves normalizadas (sem acento/caixa).
DEPT_TO_BOARD: dict[str, str] = {
    "contrato": "7428825510",      # Contratos / Captação
    "comercial": "7428822502",     # Comercial / Captação
    "operacional": "7428852961",   # Operacional / Captação
    "rh": "7439711695",            # RH / Captação
    "dp": "7428845006",            # DP / Captação
    "compras": "7428841707",       # Compras / Captação
    "sesmt": "7428895344",         # SESMT / Captação
    "financeiro": "7428847491",    # Financeiro / Captação
    "fiscal": "7428827382",        # Contabilidade - Fiscal / Captação
    "contabil": "7428827382",      # Contabilidade - Fiscal / Captação
    "t.i": "7428896809",           # TI / Captação
    "ti": "7428896809",            # TI / Captação
    "estoque": "7811252222",       # Estoque / Captação
    "limpeza": "8996283505",       # ASG / Captação (Asseio e Serviços Gerais)
}


def _norm(value: str | None) -> str:
    s = (value or "").strip().lower()
    return "".join(
        c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn"
    )


class MondayError(RuntimeError):
    pass


def _token() -> str:
    token = os.environ.get("MONDAY_API_TOKEN", "").strip()
    if not token:
        raise MondayError("MONDAY_API_TOKEN não configurada no servidor.")
    return token


def _gql(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    # Serializa explicitamente para evitar double-encoding de acentos: corpo em
    # UTF-8 com charset declarado; leitura decodificando o conteúdo como UTF-8.
    payload = json.dumps({"query": query, "variables": variables or {}}).encode("utf-8")
    resp = requests.post(
        MONDAY_API,
        data=payload,
        headers={
            "Authorization": _token(),
            "Content-Type": "application/json; charset=utf-8",
        },
        timeout=30,
    )
    try:
        body = json.loads(resp.content.decode("utf-8", "replace"))
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


def _resolve_first_asset(col_values: dict[str, Any],
                         col: dict[str, Any] | None) -> tuple[str | None, str | None]:
    """Dada uma coluna 'file', resolve (public_url, nome) do primeiro anexo.

    Devolve (None, None) se não houver coluna, anexo ou se a API falhar.
    """
    if not col:
        return None, None
    raw = (col_values.get(col["id"], {}) or {}).get("value")
    if not raw:
        return None, None
    asset_ids: list[str] = []
    try:
        parsed = json.loads(raw)
        for f in parsed.get("files", []):
            aid = f.get("assetId") or f.get("asset_id")
            if aid:
                asset_ids.append(str(aid))
    except (ValueError, AttributeError):
        return None, None
    if not asset_ids:
        return None, None
    assets = _gql(
        "query ($aids: [ID!]!) { assets (ids: $aids) { id name public_url } }",
        {"aids": asset_ids},
    ).get("assets") or []
    if assets:
        return assets[0].get("public_url"), assets[0].get("name")
    return None, None


def get_item_context(item_id: str | int) -> dict[str, Any]:
    """Lê o item: nome, IDs das colunas (status/arquivo), etiqueta atual e a
    URL pública (temporária) do currículo anexado."""
    data = _gql(
        """
        query ($ids: [ID!]!) {
          items (ids: $ids) {
            id
            name
            url
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

    def _txt(col: dict[str, Any] | None) -> str | None:
        if not col:
            return None
        return (col_values.get(col["id"], {}) or {}).get("text") or None

    status_col = _match_col(columns, STATUS_COL_TITLES, col_type="status")
    file_col = _match_col(columns, FILE_COL_TITLES, col_type="file")
    if not status_col:
        raise MondayError("Coluna de status 'Avaliação de Currículo' não encontrada.")
    if not file_col:
        raise MondayError("Coluna de arquivo 'Anexe seu currículo' não encontrada.")

    status_now = (col_values.get(status_col["id"], {}) or {}).get("text") or ""

    # Currículo e Laudo Atualizado: dois anexos distintos do mesmo item.
    cv_url, cv_name = _resolve_first_asset(col_values, file_col)
    laudo_col = _match_col(columns, LAUDO_COL_TITLES, col_type="file")
    laudo_url, laudo_name = _resolve_first_asset(col_values, laudo_col)

    return {
        "item_id": str(item.get("id")),
        "board_id": str(board.get("id")),
        "name": item.get("name"),
        "url": item.get("url"),
        "status_column_id": status_col["id"],
        "status_atual": status_now,
        "cv_url": cv_url,
        "cv_name": cv_name,
        "departamento": _txt(_match_col(columns, ("departamento",), "status")),
        "cargo": _txt(_match_col(columns, ("cargo",), "status")),
        "email": _txt(_match_col(columns, ("mail",))),
        "telefone": _txt(_match_col(columns, ("telefone", "fone", "celular"))),
        # Campos PCD (consultivos — não alteram a triagem por mérito).
        "pcd": _txt(_match_col(columns, PCD_COL_TITLES)),
        "pcd_especificacao": _txt(_match_col(columns, PCD_ESPEC_COL_TITLES)),
        "laudo_url": laudo_url,
        "laudo_name": laudo_name,
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


# ---------------------------------------------------------------------------
# Cópia para o board de Captação do setor (4ª etapa)
# ---------------------------------------------------------------------------
def _board_meta(board_id: str) -> dict[str, Any]:
    data = _gql(
        """
        query ($b: [ID!]!) {
          boards (ids: $b) {
            groups { id title }
            columns { id title type settings_str }
          }
        }
        """,
        {"b": [str(board_id)]},
    )
    boards = data.get("boards") or []
    if not boards:
        raise MondayError(f"Board {board_id} não encontrado.")
    return boards[0]


def _board_item_names(board_id: str) -> set[str]:
    data = _gql(
        """
        query ($b: [ID!]!) {
          boards (ids: $b) { items_page (limit: 500) { items { name } } }
        }
        """,
        {"b": [str(board_id)]},
    )
    boards = data.get("boards") or []
    items = (boards[0].get("items_page", {}) or {}).get("items", []) if boards else []
    return {_norm(it.get("name")) for it in items}


def _existing_label(col: dict[str, Any], value: str) -> str | None:
    """Retorna o rótulo exato da coluna status que casa com `value` (ou None)."""
    try:
        labels = json.loads(col.get("settings_str") or "{}").get("labels", {})
    except (ValueError, AttributeError):
        return None
    target = _norm(value)
    for lbl in labels.values():
        if lbl and _norm(lbl) == target:
            return lbl
    return None


def create_item(board_id: str, group_id: str | None, name: str,
                column_values: dict[str, Any] | None = None) -> str:
    data = _gql(
        """
        mutation ($b: ID!, $g: String, $n: String!, $cv: JSON) {
          create_item (board_id: $b, group_id: $g, item_name: $n,
              column_values: $cv, create_labels_if_missing: false) { id }
        }
        """,
        {
            "b": str(board_id),
            "g": group_id,
            "n": name,
            "cv": json.dumps(column_values or {}),
        },
    )
    return str(data["create_item"]["id"])


def create_update(item_id: str, body: str) -> None:
    _gql(
        "mutation ($i: ID!, $b: String!) { create_update (item_id: $i, body: $b) { id } }",
        {"i": str(item_id), "b": body},
    )


def upload_file_to_column(item_id: str, column_id: str, filename: str,
                          file_bytes: bytes) -> None:
    """Anexa um arquivo a uma coluna 'file' (GraphQL multipart do Monday)."""
    mutation = (
        "mutation ($file: File!) { add_file_to_column "
        f'(item_id: {int(item_id)}, column_id: "{column_id}", file: $file) {{ id }} }}'
    )
    resp = requests.post(
        f"{MONDAY_API}/file",
        headers={"Authorization": _token()},
        files={
            "query": (None, mutation),
            "map": (None, json.dumps({"image": "variables.file"})),
            "image": (filename or "curriculo.pdf", file_bytes),
        },
        timeout=60,
    )
    try:
        body = resp.json()
    except ValueError:
        body = {}
    if resp.status_code >= 400 or body.get("errors"):
        raise MondayError(
            f"Falha no upload do arquivo: {body.get('errors') or resp.text[:200]}"
        )


def enviar_para_captacao(ctx: dict[str, Any], score: float | None = None,
                         classificacao: str | None = None) -> dict[str, Any]:
    """Cria a cópia do candidato aprovado no board de Captação do setor.

    Retorna um dict com o resultado (nunca lança — erros viram {"copiado": False}).
    """
    dept = (ctx.get("departamento") or "").strip()
    board_id = DEPT_TO_BOARD.get(_norm(dept))
    if not board_id:
        return {"copiado": False, "motivo": f"setor sem board de Captação: {dept or '(vazio)'}"}

    name = (ctx.get("name") or "(sem nome)").strip()
    try:
        if _norm(name) in _board_item_names(board_id):
            return {"copiado": False, "motivo": "já existe no board", "board_id": board_id}

        meta = _board_meta(board_id)
        groups = meta.get("groups") or []
        group_id = groups[0]["id"] if groups else None
        columns = meta.get("columns") or []

        # Status best-effort (só seta se o rótulo já existir no board destino).
        cv: dict[str, Any] = {}
        cargo_col = _match_col(columns, ("cargo",), "status")
        setor_col = _match_col(columns, ("setor", "setores"), "status")
        if cargo_col and ctx.get("cargo"):
            lbl = _existing_label(cargo_col, ctx["cargo"])
            if lbl:
                cv[cargo_col["id"]] = {"label": lbl}
        if setor_col and dept:
            lbl = _existing_label(setor_col, dept)
            if lbl:
                cv[setor_col["id"]] = {"label": lbl}

        new_id = create_item(board_id, group_id, name, cv)

        # Update com os dados essenciais + link para o item de origem.
        linhas = ["Triagem automática — Apto para entrevista"]
        if ctx.get("cargo"):
            linhas.append(f"Cargo pretendido: {ctx['cargo']}")
        if dept:
            linhas.append(f"Setor: {dept}")
        if score is not None:
            linhas.append(f"Score: {score}")
        if classificacao:
            linhas.append(f"Classificação: {classificacao}")
        if ctx.get("email"):
            linhas.append(f"E-mail: {ctx['email']}")
        if ctx.get("telefone"):
            linhas.append(f"Telefone: {ctx['telefone']}")
        if ctx.get("url"):
            linhas.append(f"Origem (recrutamento): {ctx['url']}")
        try:
            create_update(new_id, "\n".join(linhas))
        except MondayError:
            pass

        # Re-upload do currículo na coluna de arquivo (best-effort).
        cv_anexado = False
        file_col = _match_col(columns, ("curriculo", "currículo", "curriculos"), "file")
        if file_col and ctx.get("cv_url"):
            try:
                r = requests.get(ctx["cv_url"], timeout=30)
                r.raise_for_status()
                upload_file_to_column(
                    new_id, file_col["id"], ctx.get("cv_name") or "curriculo.pdf", r.content
                )
                cv_anexado = True
            except Exception:  # noqa: BLE001
                cv_anexado = False

        return {
            "copiado": True,
            "board_id": board_id,
            "novo_item_id": new_id,
            "cv_anexado": cv_anexado,
        }
    except MondayError as exc:
        return {"copiado": False, "motivo": str(exc), "board_id": board_id}
