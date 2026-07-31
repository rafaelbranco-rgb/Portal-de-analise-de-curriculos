"""Camada de banco de dados (PostgreSQL) para o portal.

Usa a variável de ambiente ``DATABASE_URL`` (a string de conexão fornecida pelo
Neon / Supabase). As tabelas são criadas automaticamente na primeira utilização.

Motivo: em hospedagens serverless (Vercel) o sistema de arquivos é somente
leitura, então não dá para guardar dados em arquivos JSON. Os dados ficam num
Postgres gerenciado.
"""
from __future__ import annotations

import json
import os
import threading
from contextlib import contextmanager

import psycopg2
import psycopg2.extras

# Garante que colunas json/jsonb voltem como dict/list do Python ao ler.
psycopg2.extras.register_default_json(globally=True, loads=json.loads)
psycopg2.extras.register_default_jsonb(globally=True, loads=json.loads)

_init_lock = threading.Lock()
_initialized = False

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS jobs (
    id          TEXT PRIMARY KEY,
    titulo      TEXT NOT NULL,
    descricao   TEXT NOT NULL DEFAULT '',
    requisitos  TEXT NOT NULL DEFAULT '',
    criado_em   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS analyses (
    id                TEXT PRIMARY KEY,
    criado_em         TEXT NOT NULL,
    arquivo           TEXT NOT NULL DEFAULT '',
    candidato_nome    TEXT NOT NULL DEFAULT '(sem nome)',
    curriculo_preview TEXT NOT NULL DEFAULT '',
    resultado         JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- Usuários do portal (login individual). Senha sempre em hash — nunca em texto.
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    email         TEXT NOT NULL UNIQUE,
    nome          TEXT NOT NULL DEFAULT '',
    senha_hash    TEXT NOT NULL,
    criado_em     TEXT NOT NULL,
    ultimo_acesso TEXT,
    falhas        INTEGER NOT NULL DEFAULT 0,
    bloqueado_ate TEXT
);

CREATE TABLE IF NOT EXISTS audit_events (
    id         TEXT PRIMARY KEY,
    criado_em  TEXT NOT NULL,
    category   TEXT NOT NULL,
    action     TEXT NOT NULL,
    level      TEXT NOT NULL DEFAULT 'info',
    message    TEXT NOT NULL DEFAULT '',
    meta       JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_analyses_criado_em ON analyses (criado_em DESC);
CREATE INDEX IF NOT EXISTS idx_audit_criado_em ON audit_events (criado_em DESC);

-- Cópia do currículo original, para abrir/baixar na página do candidato.
-- Colunas adicionadas depois da 1ª versão: análises antigas ficam com NULL
-- (a tela mostra "arquivo não guardado" nesses casos).
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS arquivo_mime    TEXT NOT NULL DEFAULT '';
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS arquivo_tamanho INTEGER NOT NULL DEFAULT 0;
ALTER TABLE analyses ADD COLUMN IF NOT EXISTS arquivo_bytes   BYTEA;
"""


def _dsn() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL não configurada. Defina a string de conexão do "
            "Postgres (Neon/Supabase) nas variáveis de ambiente."
        )
    return url


@contextmanager
def get_conn():
    """Abre uma conexão, faz commit no sucesso e rollback em erro."""
    conn = psycopg2.connect(_dsn())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def get_cursor():
    """Cursor com linhas em formato de dict (RealDictCursor)."""
    with get_conn() as conn:
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        try:
            yield cur
        finally:
            cur.close()


def init_db() -> None:
    """Cria as tabelas se ainda não existirem (idempotente, roda 1x por processo)."""
    global _initialized
    if _initialized:
        return
    with _init_lock:
        if _initialized:
            return
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(SCHEMA_SQL)
        _initialized = True
