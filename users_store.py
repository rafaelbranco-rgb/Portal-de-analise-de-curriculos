"""Usuários do portal (login individual) — PostgreSQL.

A senha nunca é guardada em texto: só o hash (PBKDF2-SHA256, do Werkzeug).
Todos os usuários têm o mesmo nível de acesso — quem está logado pode usar o
portal inteiro, inclusive criar e remover outros usuários.
"""
from __future__ import annotations

import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import psycopg2
from werkzeug.security import check_password_hash, generate_password_hash

from db import get_cursor, init_db

# PBKDF2 é puro hashlib — funciona em qualquer runtime (inclusive Vercel),
# sem depender do OpenSSL trazer scrypt.
HASH_METHOD = "pbkdf2:sha256"

# A tabela tem nome próprio ("users" seco colide com outro sistema que divide o
# mesmo Postgres — o CREATE TABLE IF NOT EXISTS achava a tabela alheia e as
# consultas quebravam com 'column "email" does not exist').
TABELA = "portal_users"

SENHA_MIN = 8
MAX_FALHAS = 5          # tentativas erradas antes de bloquear
BLOQUEIO_MINUTOS = 5    # tempo de bloqueio depois de estourar as tentativas

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_COLS = "id, email, nome, criado_em, ultimo_acesso"


class UserError(RuntimeError):
    """Erro com mensagem pronta para mostrar ao usuário."""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_email(email: str | None) -> str:
    return (email or "").strip().lower()


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        d = datetime.fromisoformat(value)
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def validar_email(email: str) -> str:
    email = _norm_email(email)
    if not _EMAIL_RE.match(email):
        raise UserError("Informe um e-mail válido.")
    return email


def validar_senha(senha: str) -> str:
    senha = senha or ""
    if len(senha) < SENHA_MIN:
        raise UserError(f"A senha precisa ter pelo menos {SENHA_MIN} caracteres.")
    return senha


# ---------------------------------------------------------------------------
# Consultas
# ---------------------------------------------------------------------------
def count_users() -> int:
    init_db()
    with get_cursor() as cur:
        cur.execute(f"SELECT COUNT(*) AS c FROM {TABELA}")
        return int(cur.fetchone()["c"])


def list_users() -> list[dict[str, Any]]:
    init_db()
    with get_cursor() as cur:
        cur.execute(f"SELECT {_COLS} FROM {TABELA} ORDER BY nome, email")
        return [dict(row) for row in cur.fetchall()]


def get_user(user_id: str) -> dict[str, Any] | None:
    init_db()
    with get_cursor() as cur:
        cur.execute(f"SELECT {_COLS} FROM {TABELA} WHERE id = %s", (user_id,))
        row = cur.fetchone()
        return dict(row) if row else None


def get_user_by_email(email: str) -> dict[str, Any] | None:
    init_db()
    with get_cursor() as cur:
        cur.execute(f"SELECT {_COLS} FROM {TABELA} WHERE email = %s", (_norm_email(email),))
        row = cur.fetchone()
        return dict(row) if row else None


# ---------------------------------------------------------------------------
# Escrita
# ---------------------------------------------------------------------------
def create_user(email: str, nome: str, senha: str) -> dict[str, Any]:
    init_db()
    email = validar_email(email)
    validar_senha(senha)
    item = {
        "id": str(uuid.uuid4()),
        "email": email,
        "nome": (nome or "").strip() or email.split("@")[0],
        "senha_hash": generate_password_hash(senha, method=HASH_METHOD),
        "criado_em": _now(),
    }
    try:
        with get_cursor() as cur:
            cur.execute(
                f"INSERT INTO {TABELA} (id, email, nome, senha_hash, criado_em) "
                "VALUES (%(id)s, %(email)s, %(nome)s, %(senha_hash)s, %(criado_em)s)",
                item,
            )
    except psycopg2.IntegrityError as exc:  # e-mail duplicado
        raise UserError("Já existe um usuário com esse e-mail.") from exc
    return {
        "id": item["id"],
        "email": item["email"],
        "nome": item["nome"],
        "criado_em": item["criado_em"],
        "ultimo_acesso": None,
    }


def set_password(user_id: str, senha: str) -> bool:
    init_db()
    validar_senha(senha)
    with get_cursor() as cur:
        cur.execute(
            f"UPDATE {TABELA} SET senha_hash = %s, falhas = 0, bloqueado_ate = NULL "
            "WHERE id = %s",
            (generate_password_hash(senha, method=HASH_METHOD), user_id),
        )
        return cur.rowcount > 0


def delete_user(user_id: str) -> bool:
    init_db()
    with get_cursor() as cur:
        cur.execute(f"DELETE FROM {TABELA} WHERE id = %s", (user_id,))
        return cur.rowcount > 0


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------
def autenticar(email: str, senha: str) -> dict[str, Any]:
    """Confere e-mail + senha. Devolve o usuário ou levanta ``UserError``.

    Depois de ``MAX_FALHAS`` tentativas erradas, a conta fica bloqueada por
    ``BLOQUEIO_MINUTOS`` minutos (freio simples contra tentativa e erro).
    """
    init_db()
    email = _norm_email(email)
    senha = senha or ""
    generico = "E-mail ou senha incorretos."

    # Cada gravação vai em sua própria transação: o ``get_conn`` faz rollback
    # quando uma exceção atravessa o bloco, então registrar a falha e levantar
    # o erro no mesmo bloco apagaria o contador de tentativas.
    with get_cursor() as cur:
        cur.execute(
            "SELECT id, email, nome, senha_hash, falhas, bloqueado_ate "
            f"FROM {TABELA} WHERE email = %s",
            (email,),
        )
        row = cur.fetchone()
    if not row:
        raise UserError(generico)

    agora = datetime.now(timezone.utc)
    bloqueio = _parse_iso(row.get("bloqueado_ate"))
    if bloqueio and bloqueio > agora:
        faltam = max(1, int((bloqueio - agora).total_seconds() // 60) + 1)
        raise UserError(
            f"Conta bloqueada por tentativas incorretas. "
            f"Tente novamente em {faltam} min."
        )

    if not check_password_hash(row["senha_hash"], senha):
        falhas = int(row.get("falhas") or 0) + 1
        bloqueou = falhas >= MAX_FALHAS
        with get_cursor() as cur:
            if bloqueou:
                cur.execute(
                    f"UPDATE {TABELA} SET falhas = 0, bloqueado_ate = %s WHERE id = %s",
                    (
                        (agora + timedelta(minutes=BLOQUEIO_MINUTOS)).isoformat(),
                        row["id"],
                    ),
                )
            else:
                cur.execute(
                    f"UPDATE {TABELA} SET falhas = %s WHERE id = %s", (falhas, row["id"])
                )
        if bloqueou:
            raise UserError(
                f"Conta bloqueada por {BLOQUEIO_MINUTOS} minutos após "
                f"{MAX_FALHAS} tentativas incorretas."
            )
        raise UserError(generico)

    with get_cursor() as cur:
        cur.execute(
            f"UPDATE {TABELA} SET falhas = 0, bloqueado_ate = NULL, ultimo_acesso = %s "
            "WHERE id = %s",
            (_now(), row["id"]),
        )
    return {"id": row["id"], "email": row["email"], "nome": row["nome"]}


def verificar_senha(user_id: str, senha: str) -> bool:
    """Confere a senha atual de um usuário (usado na troca de senha)."""
    init_db()
    with get_cursor() as cur:
        cur.execute(f"SELECT senha_hash FROM {TABELA} WHERE id = %s", (user_id,))
        row = cur.fetchone()
        return bool(row) and check_password_hash(row["senha_hash"], senha or "")


# ---------------------------------------------------------------------------
# Primeiro usuário
# ---------------------------------------------------------------------------
def ensure_seed_admin() -> dict[str, Any] | None:
    """Cria o 1º usuário a partir das variáveis de ambiente, se não houver nenhum.

    Só age quando a tabela está vazia — depois disso as variáveis são ignoradas
    (e podem ser removidas do painel da Vercel).

    Escotilha de recuperação: com PORTAL_ADMIN_RESET=1 a função age mesmo com a
    tabela cheia — cria o e-mail indicado se ele não existir, ou redefine a
    senha (e destrava o bloqueio) se já existir. Serve para quando ninguém
    consegue mais entrar. Como ela roda a cada requisição, a variável precisa
    ser REMOVIDA depois de entrar: enquanto estiver ligada, qualquer troca de
    senha feita na tela volta atrás.
    """
    email = _norm_email(os.environ.get("PORTAL_ADMIN_EMAIL"))
    senha = os.environ.get("PORTAL_ADMIN_SENHA") or ""
    if not email or not senha:
        return None
    forcar = _flag(os.environ.get("PORTAL_ADMIN_RESET"))
    if count_users() > 0 and not forcar:
        return None
    try:
        atual = get_user_by_email(email) if forcar else None
        if atual:
            set_password(atual["id"], senha)
            _log_recuperacao("senha_redefinida", email)
            return atual
        novo = create_user(email, os.environ.get("PORTAL_ADMIN_NOME", ""), senha)
        _log_recuperacao("criado" if forcar else "semeado", email)
        return novo
    except UserError:
        return None


def _flag(valor: str | None) -> bool:
    return (valor or "").strip().lower() in {"1", "true", "sim", "yes", "on"}


def _log_recuperacao(acao: str, email: str) -> None:
    """Registra na auditoria. Import local e à prova de falha: se a auditoria
    estiver indisponível, a recuperação do acesso não pode ser bloqueada."""
    try:
        import audit_log

        audit_log.log(
            "usuario",
            f"admin_{acao}",
            f"Acesso de administrador {acao.replace('_', ' ')} via variáveis de ambiente: {email}",
            level="warning",
            meta={"email": email, "origem": "PORTAL_ADMIN_*"},
        )
    except Exception:
        pass
