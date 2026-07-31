"""Controle de acesso do portal: login por sessão + gestão de usuários.

Por que sessão em cookie assinado (e não banco de sessões): na Vercel cada
requisição pode cair em uma instância diferente, então não existe memória
compartilhada. O cookie é assinado com a ``SECRET_KEY`` — o navegador guarda,
mas não consegue forjar.

Todo mundo que está logado tem o mesmo nível de acesso (decisão do projeto).
As rotas de automação (webhook do Monday e /api/triagem) continuam liberadas,
porque já se autenticam com token próprio.
"""
from __future__ import annotations

import hashlib
import os
from datetime import timedelta
from typing import Any

from flask import Blueprint, g, jsonify, redirect, request, session

import audit_log
import users_store
from users_store import UserError

# Tempo de inatividade até a sessão expirar.
SESSION_HORAS = 12

# Endpoints liberados sem login.
PUBLIC_ENDPOINTS = {
    "login_page",      # GET  /login            (tela de login)
    "auth.login",      # POST /api/auth/login
    "auth.status",     # GET  /api/auth/status  (a tela de login consulta)
    "monday_webhook",  # POST /api/monday-webhook (token na query string)
    "triagem",         # POST /api/triagem / /api/analise (header X-API-Key)
    "static",          # CSS, JS e logo
}

bp = Blueprint("auth", __name__, url_prefix="/api")


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
def _secret_key() -> tuple[str, bool]:
    """Devolve (chave, veio_da_variavel_de_ambiente).

    Sem ``SECRET_KEY`` configurada, deriva uma chave estável a partir de outros
    segredos que o servidor já tem. Assim o portal não fica fora do ar por
    falta de uma variável — mas o ideal é definir ``SECRET_KEY`` mesmo, porque
    trocar qualquer um dos outros segredos derruba as sessões abertas.
    """
    env = os.environ.get("SECRET_KEY", "").strip()
    if env:
        return env, True
    base = "|".join(
        os.environ.get(name, "")
        for name in ("DATABASE_URL", "MONDAY_WEBHOOK_TOKEN", "GEMINI_API_KEY")
    )
    return hashlib.sha256(f"portal-cv-sessao|{base}".encode()).hexdigest(), False


def init_app(app) -> None:
    key, from_env = _secret_key()
    app.secret_key = key
    app.config.update(
        SECRET_KEY_FROM_ENV=from_env,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # Em produção (Vercel) o portal é https; local roda em http.
        SESSION_COOKIE_SECURE=bool(os.environ.get("VERCEL")),
        PERMANENT_SESSION_LIFETIME=timedelta(hours=SESSION_HORAS),
    )
    app.register_blueprint(bp)
    app.before_request(_guard)


# ---------------------------------------------------------------------------
# Sessão
# ---------------------------------------------------------------------------
def current_user() -> dict[str, Any] | None:
    """Usuário logado nesta requisição (ou None). Cacheado por requisição."""
    if hasattr(g, "_portal_user"):
        return g._portal_user
    user: dict[str, Any] | None = None
    uid = session.get("uid")
    if uid:
        try:
            user = users_store.get_user(uid)  # None se o usuário foi removido
        except Exception:  # noqa: BLE001
            # Banco indisponível: confia na identidade do cookie (é assinado)
            # para não derrubar todo mundo por uma falha momentânea.
            user = {
                "id": uid,
                "email": session.get("email", ""),
                "nome": session.get("nome", ""),
            }
    g._portal_user = user
    return user


def _abrir_sessao(user: dict[str, Any]) -> None:
    session.clear()
    session.permanent = True
    session["uid"] = user["id"]
    session["email"] = user.get("email", "")
    session["nome"] = user.get("nome", "")
    g._portal_user = user


def _api_key_valida() -> bool:
    """Permite que scripts/automações usem a API com a chave ``TRIAGEM_API_KEY``.

    É o que mantém funcionando ferramentas sem navegador (ex.: seed_vagas.py e
    integrações), já que elas não têm como fazer login em tela.
    """
    esperada = os.environ.get("TRIAGEM_API_KEY", "").strip()
    if not esperada:
        return False
    return (request.headers.get("X-API-Key") or "").strip() == esperada


def _guard():
    """Exige login em tudo que não estiver em ``PUBLIC_ENDPOINTS``."""
    if request.method == "OPTIONS":
        return None
    if (request.endpoint or "") in PUBLIC_ENDPOINTS:
        return None
    if current_user():
        return None
    if request.path.startswith("/api/") and _api_key_valida():
        return None
    if request.path.startswith("/api/"):
        return jsonify({"error": "Faça login para continuar.", "kind": "auth"}), 401
    return redirect("/login")


def _publico(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user.get("id"),
        "nome": user.get("nome"),
        "email": user.get("email"),
        "criado_em": user.get("criado_em"),
        "ultimo_acesso": user.get("ultimo_acesso"),
    }


# ---------------------------------------------------------------------------
# Rotas de login
# ---------------------------------------------------------------------------
@bp.get("/auth/status")
def status():
    """Estado do acesso — usado pela tela de login (não exige sessão)."""
    try:
        users_store.ensure_seed_admin()
        total = users_store.count_users()
        banco_ok = True
    except Exception as exc:  # noqa: BLE001
        return jsonify(
            {
                "logado": False,
                "banco_ok": False,
                "sem_usuarios": False,
                "erro": f"Banco de dados indisponível: {exc}",
            }
        ), 200
    user = current_user()
    return jsonify(
        {
            "logado": bool(user),
            "banco_ok": banco_ok,
            "sem_usuarios": total == 0,
            "usuario": _publico(user) if user else None,
        }
    )


@bp.post("/auth/login")
def login():
    payload = request.get_json(silent=True) or {}
    email = (payload.get("email") or "").strip()
    senha = payload.get("senha") or ""
    if not email or not senha:
        return jsonify({"error": "Informe e-mail e senha.", "kind": "input"}), 400

    try:
        users_store.ensure_seed_admin()
        user = users_store.autenticar(email, senha)
    except UserError as exc:
        audit_log.log(
            "acesso",
            "login_falhou",
            f"Tentativa de login recusada: {email}",
            level="warn",
            meta={"email": email.lower(), "motivo": str(exc)},
        )
        return jsonify({"error": str(exc), "kind": "auth"}), 401
    except Exception as exc:  # noqa: BLE001
        return jsonify(
            {"error": f"Falha ao consultar usuários: {exc}", "kind": "config"}
        ), 500

    _abrir_sessao(user)
    audit_log.log(
        "acesso", "login", f"Entrou no portal: {user.get('nome') or user['email']}"
    )
    return jsonify({"ok": True, "usuario": _publico(user)})


@bp.post("/auth/logout")
def logout():
    user = current_user()
    if user:
        audit_log.log(
            "acesso", "logout", f"Saiu do portal: {user.get('nome') or user['email']}"
        )
    session.clear()
    g._portal_user = None
    return jsonify({"ok": True})


@bp.get("/auth/me")
def me():
    user = current_user()
    if not user:
        return jsonify({"error": "Faça login para continuar.", "kind": "auth"}), 401
    return jsonify(_publico(user))


@bp.post("/auth/senha")
def trocar_senha():
    """Troca a senha do próprio usuário (exige a senha atual)."""
    user = current_user()
    payload = request.get_json(silent=True) or {}
    atual = payload.get("senha_atual") or ""
    nova = payload.get("nova_senha") or ""
    if not users_store.verificar_senha(user["id"], atual):
        return jsonify({"error": "Senha atual incorreta.", "kind": "auth"}), 400
    try:
        users_store.set_password(user["id"], nova)
    except UserError as exc:
        return jsonify({"error": str(exc), "kind": "input"}), 400
    audit_log.log("usuario", "senha_alterada", "Senha alterada pelo próprio usuário")
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Rotas de usuários (qualquer pessoa logada — todos têm o mesmo nível)
# ---------------------------------------------------------------------------
@bp.get("/users")
def listar_usuarios():
    atual = current_user()
    users = users_store.list_users()
    for u in users:
        u["eu"] = u["id"] == atual["id"]
    return jsonify(users)


@bp.post("/users")
def criar_usuario():
    payload = request.get_json(silent=True) or {}
    try:
        novo = users_store.create_user(
            payload.get("email") or "",
            payload.get("nome") or "",
            payload.get("senha") or "",
        )
    except UserError as exc:
        return jsonify({"error": str(exc), "kind": "input"}), 400
    audit_log.log(
        "usuario",
        "create",
        f"Usuário criado: {novo['nome']} ({novo['email']})",
        meta={"usuario_criado": novo["email"]},
    )
    return jsonify(novo), 201


@bp.delete("/users/<user_id>")
def remover_usuario(user_id: str):
    atual = current_user()
    if user_id == atual["id"]:
        return jsonify(
            {"error": "Você não pode remover o seu próprio acesso.", "kind": "input"}
        ), 400
    if users_store.count_users() <= 1:
        return jsonify(
            {"error": "É preciso manter pelo menos um usuário.", "kind": "input"}
        ), 400
    alvo = users_store.get_user(user_id)
    if not alvo or not users_store.delete_user(user_id):
        return jsonify({"error": "Usuário não encontrado."}), 404
    audit_log.log(
        "usuario",
        "delete",
        f"Usuário removido: {alvo['nome']} ({alvo['email']})",
        level="warn",
        meta={"usuario_removido": alvo["email"]},
    )
    return jsonify({"ok": True})


@bp.post("/users/<user_id>/senha")
def redefinir_senha(user_id: str):
    """Redefine a senha de outro usuário (quem esqueceu pede a um colega)."""
    alvo = users_store.get_user(user_id)
    if not alvo:
        return jsonify({"error": "Usuário não encontrado."}), 404
    payload = request.get_json(silent=True) or {}
    try:
        users_store.set_password(user_id, payload.get("senha") or "")
    except UserError as exc:
        return jsonify({"error": str(exc), "kind": "input"}), 400
    audit_log.log(
        "usuario",
        "senha_redefinida",
        f"Senha redefinida para: {alvo['nome']} ({alvo['email']})",
        level="warn",
        meta={"usuario_alvo": alvo["email"]},
    )
    return jsonify({"ok": True})
