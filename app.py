"""Portal de análise de currículos — Flask app."""
from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import unquote, urlparse

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

import analyses_store
import audit_log
import jobs_store
import monday_client
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
# Triagem automática (n8n / Monday)
# ---------------------------------------------------------------------------
# Endpoint pensado para automação: recebe um JSON simples (URL do currículo
# anexado no Monday + metadados do formulário), baixa o arquivo, roda a mesma
# análise do /api/analyze e devolve o `score` e `apto` já no topo da resposta,
# para o n8n usar direto num nó "If" (score >= 7.0).
_CONTENT_TYPE_EXT = {
    "application/pdf": ".pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "text/plain": ".txt",
}


def _filename_from_download(url: str, resp: requests.Response) -> str:
    """Descobre um nome de arquivo (com extensão) a partir do download."""
    cd = resp.headers.get("Content-Disposition", "")
    m = re.search(r'filename\*?=(?:UTF-8\'\')?"?([^";]+)', cd)
    if m:
        return unquote(m.group(1).strip())
    path = urlparse(url).path
    name = unquote(os.path.basename(path))
    if name:
        return name
    ext = _CONTENT_TYPE_EXT.get(
        (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower(),
        ".pdf",
    )
    return f"curriculo{ext}"


def _ensure_supported_name(arquivo: str, resp: requests.Response) -> str:
    """Garante uma extensão suportada (PDF/DOCX/TXT), inferindo do Content-Type."""
    ext = Path(arquivo).suffix.lower()
    if ext in {".pdf", ".docx", ".txt"}:
        return arquivo
    ctype = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    guessed = _CONTENT_TYPE_EXT.get(ctype)
    if guessed:
        return arquivo + guessed
    return arquivo


@app.post("/api/triagem")
@app.post("/api/analise")
def triagem():
    expected = os.environ.get("TRIAGEM_API_KEY", "").strip()
    if not expected:
        return jsonify(
            {"error": "TRIAGEM_API_KEY não configurada no servidor.", "kind": "config"}
        ), 500
    provided = (request.headers.get("X-API-Key") or "").strip()
    if provided != expected:
        return jsonify({"error": "Não autorizado.", "kind": "auth"}), 401

    payload = request.get_json(silent=True) or {}
    file_url = (payload.get("file_url") or "").strip()
    curriculo_texto_in = (payload.get("curriculo_texto") or "").strip()
    candidato_nome_in = (payload.get("candidato_nome") or "").strip()
    cargo = (payload.get("cargo_pretendido") or "").strip()
    item_id = payload.get("item_id")
    try:
        threshold = float(payload.get("threshold") or 7.0)
    except (TypeError, ValueError):
        threshold = 7.0

    arquivo = "(texto via n8n)"
    if curriculo_texto_in:
        curriculo_texto = curriculo_texto_in
    elif file_url:
        try:
            resp = requests.get(file_url, timeout=30)
            resp.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            return jsonify(
                {"error": f"Falha ao baixar o currículo: {exc}", "kind": "input"}
            ), 400
        raw = resp.content
        if not raw:
            return jsonify({"error": "Arquivo do currículo veio vazio.", "kind": "input"}), 400
        if len(raw) > MAX_UPLOAD_SIZE:
            return jsonify(
                {"error": f"Currículo maior que o limite ({MAX_UPLOAD_SIZE // (1024 * 1024)} MB).",
                 "kind": "input"}
            ), 413
        arquivo = _ensure_supported_name(_filename_from_download(file_url, resp), resp)
        try:
            curriculo_texto = extract_text(arquivo, raw)
        except UnsupportedFileError as exc:
            return jsonify({"error": str(exc), "kind": "input"}), 400
        except Exception as exc:  # noqa: BLE001
            return jsonify({"error": f"Falha ao ler o arquivo: {exc}", "kind": "input"}), 400
    else:
        return jsonify(
            {"error": "Envie 'file_url' (URL do currículo) ou 'curriculo_texto'.",
             "kind": "input"}
        ), 400

    if not curriculo_texto.strip():
        return jsonify(
            {"error": "Não foi possível extrair texto do currículo (PDF escaneado?).",
             "kind": "input"}
        ), 400

    vagas = jobs_store.list_jobs()
    if not vagas:
        return jsonify(
            {"error": "Nenhuma vaga cadastrada no portal.", "kind": "config"}
        ), 400

    try:
        resultado = analisar_curriculo(curriculo_texto, vagas)
    except AnalyzerError as exc:
        status = 429 if exc.kind == "quota" else 502
        out: dict[str, object] = {"error": str(exc), "kind": exc.kind}
        if exc.retry_after is not None:
            out["retry_after"] = exc.retry_after
        return jsonify(out), status

    candidato_nome = (
        candidato_nome_in
        or (resultado.get("candidato_nome") or "").strip()
        or "(sem nome)"
    )
    score = round(float(resultado.get("score_final") or 0), 1)
    apto = score >= threshold

    saved = analyses_store.save_analysis(
        arquivo=arquivo,
        candidato_nome=candidato_nome,
        resultado=resultado,
        curriculo_preview=curriculo_texto,
    )

    audit_log.log(
        "triagem",
        "completed",
        f"Triagem n8n: {candidato_nome} — {score:.1f}/10 — "
        f"{'APTO' if apto else 'não apto'}",
        meta={
            "analise_id": saved["id"],
            "candidato": candidato_nome,
            "score": score,
            "apto": apto,
            "threshold": threshold,
            "cargo_pretendido": cargo or None,
            "item_id": item_id,
            "arquivo": arquivo,
        },
    )

    return jsonify(
        {
            "score": score,
            "apto": apto,
            "threshold": threshold,
            "classificacao": resultado.get("classificacao"),
            "recomendacao_final": resultado.get("recomendacao_final"),
            "vaga_recomendada": (resultado.get("vaga_recomendada") or {}).get("titulo"),
            "candidato_nome": candidato_nome,
            "item_id": item_id,
            "analise_id": saved["id"],
            "criado_em": saved["criado_em"],
            "resultado": resultado,
        }
    )


# ---------------------------------------------------------------------------
# Triagem automática DIRETA do Monday (sem n8n)
# ---------------------------------------------------------------------------
# O Monday (Integrar → Webhook) chama esta rota quando um currículo é cadastrado.
# O portal lê o CV anexado, analisa e escreve a etiqueta de avaliação de volta:
#   score >= TRIAGEM_THRESHOLD  → APROV.ENTREVISTA
#   score <  TRIAGEM_THRESHOLD  → REPROV.TRIAGEM  (se TRIAGEM_REPROVAR=1)
def _download_and_extract(file_url: str) -> tuple[str, str]:
    """Baixa o arquivo da URL e devolve (nome_arquivo, texto_extraído)."""
    resp = requests.get(file_url, timeout=30)
    resp.raise_for_status()
    raw = resp.content
    if not raw:
        raise UnsupportedFileError("Arquivo do currículo veio vazio.")
    if len(raw) > MAX_UPLOAD_SIZE:
        raise UnsupportedFileError(
            f"Currículo maior que o limite ({MAX_UPLOAD_SIZE // (1024 * 1024)} MB)."
        )
    arquivo = _ensure_supported_name(_filename_from_download(file_url, resp), resp)
    return arquivo, extract_text(arquivo, raw)


# Rótulos da coluna PCD que significam "não é PCD / não declarado".
_PCD_NEGATIVOS = {"", "nao", "não", "nao identificado", "não identificado",
                  "nao informado", "não informado", "n/a", "na", "-"}


def _build_pcd_context(ctx: dict[str, object]) -> dict[str, object] | None:
    """Monta o contexto de PCD para a análise (consultivo).

    Retorna None quando não há nenhum sinal de PCD. Caso haja, baixa e extrai o
    texto do Laudo Atualizado (best-effort) para enriquecer o parecer.
    """
    pcd_raw = (ctx.get("pcd") or "").strip()
    espec = (ctx.get("pcd_especificacao") or "").strip()
    laudo_url = ctx.get("laudo_url")

    pcd_norm = pcd_raw.lower().strip()
    declarou_pcd = bool(pcd_raw) and pcd_norm not in _PCD_NEGATIVOS
    if not (declarou_pcd or espec or laudo_url):
        return None

    laudo_texto = ""
    if laudo_url:
        try:
            _laudo_nome, laudo_texto = _download_and_extract(laudo_url)
        except Exception:  # noqa: BLE001 — laudo ilegível não pode quebrar a triagem
            laudo_texto = ""

    return {
        "pcd": pcd_raw or "Não informado",
        "especificacao": espec or "Não informado",
        "laudo_texto": laudo_texto,
    }


@app.post("/api/monday-webhook")
def monday_webhook():
    payload = request.get_json(silent=True) or {}

    # 1) Handshake do Monday: ecoa o "challenge" na configuração do webhook.
    if "challenge" in payload:
        return jsonify({"challenge": payload["challenge"]})

    # 2) Autenticação por token na query string (?token=...), pois o webhook
    #    nativo do Monday não envia headers customizados.
    expected = os.environ.get("MONDAY_WEBHOOK_TOKEN", "").strip()
    if expected and (request.args.get("token") or "").strip() != expected:
        return jsonify({"error": "Não autorizado."}), 401

    event = payload.get("event") or {}
    item_id = event.get("pulseId") or event.get("itemId")
    if not item_id:
        return jsonify({"ok": True, "ignored": "sem pulseId no evento"}), 200

    label_aprov = os.environ.get("TRIAGEM_LABEL_APROVADO", "APROV.ENTREVISTA").strip()
    label_reprov = os.environ.get("TRIAGEM_LABEL_REPROVADO", "REPROV.TRIAGEM").strip()
    reprovar = os.environ.get("TRIAGEM_REPROVAR", "1").strip() not in ("0", "false", "")
    try:
        threshold = float(os.environ.get("TRIAGEM_THRESHOLD", "7.0"))
    except ValueError:
        threshold = 7.0

    try:
        ctx = monday_client.get_item_context(item_id)
    except monday_client.MondayError as exc:
        audit_log.log("triagem", "failed", f"Monday: {exc}", level="error",
                      meta={"item_id": item_id})
        return jsonify({"error": str(exc)}), 502

    # 3) Idempotência: se já tem etiqueta final, ignora reenvios do webhook.
    if ctx["status_atual"] in (label_aprov, label_reprov):
        return jsonify({"ok": True, "skipped": "já triado", "status": ctx["status_atual"]}), 200

    if not ctx.get("cv_url"):
        audit_log.log("triagem", "rejected",
                      f"Sem currículo anexado: {ctx.get('name')}", level="warn",
                      meta={"item_id": item_id})
        return jsonify({"ok": True, "ignored": "sem currículo anexado"}), 200

    # 4) Baixa + extrai + analisa.
    try:
        arquivo, curriculo_texto = _download_and_extract(ctx["cv_url"])
    except Exception as exc:  # noqa: BLE001
        audit_log.log("triagem", "extract_failed", f"Falha ao ler CV: {exc}",
                      level="error", meta={"item_id": item_id})
        return jsonify({"error": f"Falha ao ler o currículo: {exc}"}), 400

    if not curriculo_texto.strip():
        audit_log.log("triagem", "rejected",
                      "CV sem texto extraível (PDF escaneado?)", level="warn",
                      meta={"item_id": item_id})
        return jsonify({"ok": True, "ignored": "sem texto extraível"}), 200

    vagas = jobs_store.list_jobs()
    if not vagas:
        return jsonify({"error": "Nenhuma vaga cadastrada no portal."}), 400

    # 4b) Contexto de PCD (consultivo): só monta se houver sinal de PCD —
    #     etiqueta PCD afirmativa, especificação preenchida ou laudo anexado.
    #     O laudo é baixado e lido para um parecer mais preciso; falha de leitura
    #     não interrompe a triagem (segue com o que houver).
    pcd_context = _build_pcd_context(ctx)

    try:
        resultado = analisar_curriculo(curriculo_texto, vagas, pcd_context=pcd_context)
    except AnalyzerError as exc:
        status = 429 if exc.kind == "quota" else 502
        audit_log.log("triagem", "failed", f"Falha na análise: {exc}", level="error",
                      meta={"item_id": item_id, "kind": exc.kind})
        return jsonify({"error": str(exc), "kind": exc.kind}), status

    candidato_nome = (
        (resultado.get("candidato_nome") or "").strip()
        or ctx.get("name")
        or "(sem nome)"
    )
    score = round(float(resultado.get("score_final") or 0), 1)
    apto = score >= threshold

    # 5) Escreve a etiqueta de volta no Monday.
    novo_status = label_aprov if apto else label_reprov
    if apto or reprovar:
        try:
            monday_client.set_status(
                ctx["board_id"], ctx["item_id"], ctx["status_column_id"], novo_status
            )
        except monday_client.MondayError as exc:
            audit_log.log("triagem", "failed",
                          f"Falha ao atualizar etiqueta: {exc}", level="error",
                          meta={"item_id": item_id})
            return jsonify({"error": str(exc)}), 502

    # 5b) Aprovado -> cria a cópia no board de Captação do setor (4ª etapa).
    #     Não derruba a triagem se a cópia falhar (a etiqueta já foi gravada).
    captacao = None
    if apto:
        try:
            captacao = monday_client.enviar_para_captacao(
                ctx, score=score, classificacao=resultado.get("classificacao")
            )
        except Exception as exc:  # noqa: BLE001
            captacao = {"copiado": False, "motivo": f"erro inesperado: {exc}"}
        audit_log.log(
            "triagem",
            "captacao" if (captacao or {}).get("copiado") else "captacao_skip",
            f"Captação ({ctx.get('departamento') or 'sem setor'}): "
            f"{'copiado' if (captacao or {}).get('copiado') else (captacao or {}).get('motivo')}",
            level="info" if (captacao or {}).get("copiado") else "warn",
            meta={"item_id": ctx["item_id"], "candidato": candidato_nome, **(captacao or {})},
        )

    saved = analyses_store.save_analysis(
        arquivo=arquivo, candidato_nome=candidato_nome,
        resultado=resultado, curriculo_preview=curriculo_texto,
    )
    audit_log.log(
        "triagem", "completed",
        f"Triagem Monday: {candidato_nome} — {score:.1f}/10 — {novo_status}",
        meta={"analise_id": saved["id"], "candidato": candidato_nome, "score": score,
              "apto": apto, "threshold": threshold, "item_id": ctx["item_id"],
              "status_aplicado": novo_status if (apto or reprovar) else ctx["status_atual"],
              "pcd_indicador": (resultado.get("analise_pcd") or {}).get("indicador")},
    )

    return jsonify({
        "ok": True, "candidato_nome": candidato_nome, "score": score,
        "apto": apto, "status_aplicado": novo_status if (apto or reprovar) else None,
        "analise_id": saved["id"], "captacao": captacao,
    })


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
