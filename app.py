"""Portal de análise de currículos — Flask app."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import analyses_store
import audit_log
import jobs_store
from analyzer import AnalyzerError, analisar_curriculo
from extractor import UnsupportedFileError, extract_text


load_dotenv()

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

MAX_UPLOAD_SIZE = 8 * 1024 * 1024  # 8 MB

app = Flask(__name__, static_folder=str(STATIC_DIR), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_SIZE
CORS(app)


# ---------------------------------------------------------------------------
# Rotas estáticas (SPA)
# ---------------------------------------------------------------------------
@app.get("/")
def index() -> object:
    return send_from_directory(STATIC_DIR, "index.html")


# ---------------------------------------------------------------------------
# CRUD de vagas
# ---------------------------------------------------------------------------
@app.get("/api/jobs")
def list_jobs():
    return jsonify(jobs_store.list_jobs())


@app.post("/api/jobs")
def create_job():
    payload = request.get_json(silent=True) or {}
    titulo = (payload.get("titulo") or "").strip()
    descricao = (payload.get("descricao") or "").strip()
    requisitos = (payload.get("requisitos") or "").strip()
    if not titulo or not descricao:
        return jsonify({"error": "Título e descrição são obrigatórios."}), 400
    job = jobs_store.create_job(titulo, descricao, requisitos)
    audit_log.log(
        "vaga",
        "create",
        f"Vaga criada: {job['titulo']}",
        meta={"vaga_id": job["id"], "titulo": job["titulo"]},
    )
    return jsonify(job), 201


@app.put("/api/jobs/<job_id>")
def update_job(job_id: str):
    payload = request.get_json(silent=True) or {}
    before = jobs_store.get_job(job_id)
    job = jobs_store.update_job(
        job_id,
        titulo=payload.get("titulo"),
        descricao=payload.get("descricao"),
        requisitos=payload.get("requisitos"),
    )
    if not job:
        return jsonify({"error": "Vaga não encontrada."}), 404
    changed_fields = []
    if before:
        for f in ("titulo", "descricao", "requisitos"):
            if (before.get(f) or "") != (job.get(f) or ""):
                changed_fields.append(f)
    audit_log.log(
        "vaga",
        "update",
        f"Vaga atualizada: {job['titulo']}",
        meta={
            "vaga_id": job["id"],
            "titulo": job["titulo"],
            "campos_alterados": changed_fields,
        },
    )
    return jsonify(job)


@app.delete("/api/jobs/<job_id>")
def delete_job(job_id: str):
    before = jobs_store.get_job(job_id)
    ok = jobs_store.delete_job(job_id)
    if not ok:
        return jsonify({"error": "Vaga não encontrada."}), 404
    audit_log.log(
        "vaga",
        "delete",
        f"Vaga excluída: {before['titulo'] if before else job_id}",
        level="warn",
        meta={"vaga_id": job_id, "titulo": before["titulo"] if before else None},
    )
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Análise de currículo
# ---------------------------------------------------------------------------
@app.post("/api/analyze")
def analyze():
    if "curriculo" not in request.files:
        return jsonify({"error": "Envie o currículo no campo 'curriculo'."}), 400

    uploaded = request.files["curriculo"]
    if not uploaded.filename:
        return jsonify({"error": "Arquivo sem nome."}), 400

    raw = uploaded.read()
    if not raw:
        return jsonify({"error": "Arquivo vazio."}), 400

    try:
        curriculo_texto = extract_text(uploaded.filename, raw)
    except UnsupportedFileError as exc:
        audit_log.log(
            "analise",
            "rejected",
            f"Arquivo recusado: {uploaded.filename}",
            level="warn",
            meta={"arquivo": uploaded.filename, "motivo": str(exc)},
        )
        return jsonify({"error": str(exc), "kind": "input"}), 400
    except Exception as exc:  # noqa: BLE001
        audit_log.log(
            "analise",
            "extract_failed",
            f"Falha ao ler arquivo: {uploaded.filename}",
            level="error",
            meta={"arquivo": uploaded.filename, "erro": str(exc)},
        )
        return jsonify({"error": f"Falha ao ler o arquivo: {exc}"}), 400

    if not curriculo_texto.strip():
        return (
            jsonify(
                {
                    "error": (
                        "Não foi possível extrair texto do arquivo. Se for um "
                        "PDF escaneado (apenas imagens), converta para PDF "
                        "com texto pesquisável ou envie em DOCX."
                    ),
                    "kind": "input",
                }
            ),
            400,
        )

    vagas = jobs_store.list_jobs()
    if not vagas:
        return jsonify(
            {"error": "Nenhuma vaga cadastrada. Cadastre vagas antes de analisar."}
        ), 400

    try:
        resultado = analisar_curriculo(curriculo_texto, vagas)
    except AnalyzerError as exc:
        status = 429 if exc.kind == "quota" else 502
        payload: dict[str, object] = {"error": str(exc), "kind": exc.kind}
        if exc.retry_after is not None:
            payload["retry_after"] = exc.retry_after
        audit_log.log(
            "analise",
            "failed",
            f"Falha na análise: {uploaded.filename}",
            level="error",
            meta={
                "arquivo": uploaded.filename,
                "kind": exc.kind,
                "mensagem": str(exc)[:200],
            },
        )
        return jsonify(payload), status

    candidato_nome = (resultado.get("candidato_nome") or "").strip() or "(sem nome)"

    saved = analyses_store.save_analysis(
        arquivo=uploaded.filename,
        candidato_nome=candidato_nome,
        resultado=resultado,
        curriculo_preview=curriculo_texto,
    )

    audit_log.log(
        "analise",
        "completed",
        f"Análise concluída: {candidato_nome} — "
        f"{resultado.get('classificacao', '?')} "
        f"({(resultado.get('score_final') or 0):.1f}/10)",
        meta={
            "analise_id": saved["id"],
            "candidato": candidato_nome,
            "arquivo": uploaded.filename,
            "score": resultado.get("score_final"),
            "classificacao": resultado.get("classificacao"),
            "vaga_recomendada": (resultado.get("vaga_recomendada") or {}).get(
                "titulo"
            ),
            "ia_probabilidade": (resultado.get("deteccao_ia") or {}).get(
                "probabilidade"
            ),
            "modelo": resultado.get("_model_used"),
        },
    )

    return jsonify(
        {
            "id": saved["id"],
            "criado_em": saved["criado_em"],
            "resultado": resultado,
            "arquivo": uploaded.filename,
            "candidato_nome": candidato_nome,
            "tamanho_texto": len(curriculo_texto),
        }
    )


# ---------------------------------------------------------------------------
# Histórico de análises
# ---------------------------------------------------------------------------
@app.get("/api/analyses")
def list_analyses():
    return jsonify(analyses_store.list_analyses())


@app.get("/api/analyses/<analysis_id>")
def get_analysis(analysis_id: str):
    item = analyses_store.get_analysis(analysis_id)
    if not item:
        return jsonify({"error": "Análise não encontrada."}), 404
    return jsonify(item)


@app.delete("/api/analyses/<analysis_id>")
def delete_analysis(analysis_id: str):
    before = analyses_store.get_analysis(analysis_id)
    ok = analyses_store.delete_analysis(analysis_id)
    if not ok:
        return jsonify({"error": "Análise não encontrada."}), 404
    audit_log.log(
        "analise",
        "delete",
        f"Análise excluída: {before['candidato_nome'] if before else analysis_id}",
        level="warn",
        meta={
            "analise_id": analysis_id,
            "candidato": before["candidato_nome"] if before else None,
        },
    )
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Auditoria
# ---------------------------------------------------------------------------
@app.get("/api/audit")
def list_audit():
    limit = min(int(request.args.get("limit", 200)), 500)
    category = request.args.get("category") or None
    level = request.args.get("level") or None
    return jsonify(
        audit_log.list_events(limit=limit, category=category, level=level)
    )


@app.delete("/api/audit")
def clear_audit():
    count = audit_log.clear_events()
    audit_log.log(
        "sistema",
        "audit_cleared",
        f"Histórico de auditoria limpo ({count} eventos)",
        level="warn",
    )
    return jsonify({"ok": True, "removidos": count})


# ---------------------------------------------------------------------------
# Saúde / config
# ---------------------------------------------------------------------------
@app.get("/api/health")
def health():
    return jsonify(
        {
            "ok": True,
            "gemini_configured": bool(os.environ.get("GEMINI_API_KEY", "").strip()),
            "model": os.environ.get("GEMINI_MODEL", "gemini-2.5-pro"),
        }
    )


@app.errorhandler(413)
def too_large(_e):
    audit_log.log(
        "analise",
        "rejected",
        f"Upload excedeu o limite de {MAX_UPLOAD_SIZE // (1024 * 1024)} MB",
        level="warn",
    )
    return (
        jsonify(
            {"error": f"Arquivo maior que o limite ({MAX_UPLOAD_SIZE // (1024 * 1024)} MB)."}
        ),
        413,
    )


@app.errorhandler(500)
def server_error(e):
    audit_log.log(
        "sistema",
        "error",
        f"Erro interno: {e}",
        level="error",
    )
    return jsonify({"error": "Erro interno do servidor."}), 500


if __name__ == "__main__":
    port = int(os.environ.get("FLASK_PORT", "5000"))
    app.run(host="127.0.0.1", port=port, debug=True)
