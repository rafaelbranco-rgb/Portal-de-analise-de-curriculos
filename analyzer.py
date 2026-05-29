"""Integração com Gemini para análise de currículos."""
from __future__ import annotations

import json
import os
import re
from typing import Any

import google.generativeai as genai
from google.api_core import exceptions as gax


SYSTEM_INSTRUCTIONS = """Você é um agente especialista em RH que analisa currículos para a empresa.
Você é rigoroso, objetivo, conservador e segue estritamente os critérios definidos.

REGRAS DE CONSISTÊNCIA (importantes):
- Para o MESMO currículo e MESMAS vagas, suas notas devem ser IDÊNTICAS entre execuções.
  Não introduza variação subjetiva — siga estritamente os anchors numéricos.
- Se ficar em dúvida entre dois valores, escolha SEMPRE o MENOR (postura conservadora).
- Avalie cada critério de forma independente, sem deixar uma impressão geral contaminar
  notas individuais.

Sua resposta SEMPRE deve ser um JSON válido, sem texto adicional antes ou depois,
sem cercas de markdown (```), sem comentários."""


PROMPT_TEMPLATE = """## CONTEXTO
A empresa Contato Facilities atua com terceirização (limpeza, conservação,
manutenção predial), atendimento hospitalar e administração de contratos
públicos em várias localidades (Manaus/AM, João Pessoa/PB, Tefé/AM,
Frederico Westphalen/RS).

Você precisa avaliar o currículo abaixo, comparando-o com TODAS as vagas
disponíveis. Identifique para qual vaga o candidato é mais indicado, calcule
um score ponderado para CADA vaga, e detecte se o currículo foi gerado por IA.

IMPORTANTE: existem MUITAS vagas (50+). Avalie TODAS, mas seja eficiente:
- Para vagas com BAIXA aderência (score < 4): justificativa curta (1 linha)
- Para vagas com MÉDIA ou ALTA aderência: justificativa mais detalhada
- A "vaga_recomendada" deve ser SEMPRE a de maior score real, NÃO um chute
- Considere a LOCALIDADE da vaga vs do candidato: se vagas e CV são de cidades
  diferentes, NÃO descarte automaticamente, mas registre em pontos de atenção

## VAGAS DISPONÍVEIS
{vagas_block}

## CURRÍCULO DO CANDIDATO
\"\"\"
{curriculo_texto}
\"\"\"

## CRITÉRIOS DE AVALIAÇÃO (notas de 0 a 10, com pesos)
- Experiência relevante na função (peso 3)
- Conhecimentos técnicos obrigatórios (peso 3)
- Formação acadêmica (peso 2)
- Soft skills evidenciadas (peso 1)
- Estabilidade e progressão de carreira (peso 1)

Score ponderado = (exp*3 + tec*3 + form*2 + soft*1 + estab*1) / 10

## ÂNCORAS NUMÉRICAS (siga exatamente — não use valores intermediários sem evidência)
Para CADA critério, use os anchors abaixo:
- 0  → nenhuma evidência no currículo
- 2  → evidência marginal / não-relacionada à função
- 4  → evidência fraca / parcialmente aderente
- 6  → evidência suficiente, com lacunas claras
- 8  → evidência forte e direta, atende ao requisito
- 10 → evidência completa, exemplar, supera o requisito

Casos especiais:
- Candidato SUPERQUALIFICADO para uma vaga (ex.: sênior aplicando para vaga júnior/estágio):
  conte como ponto de atenção e NÃO infle o score; mantenha "Média" ou "Baixa".
- Candidato SUBQUALIFICADO (não atende requisitos mínimos): score do critério ≤ 4.
- Pré-requisito formal não atendido (CNH, gênero, escolaridade exigida): experiência = 0
  para essa vaga específica, mesmo se houver experiências adjacentes.

## CLASSIFICAÇÃO
- 8.0 a 10.0 → "Alta aderência" (recomendado para entrevista)
- 6.0 a 7.9  → "Média aderência" (avaliar com ressalvas)
- abaixo de 6.0 → "Baixa aderência" (não recomendado)

## DETECÇÃO DE IA
Avalie a probabilidade (0-100) de o currículo ter sido GERADO POR IA, observando:
- Linguagem genérica e excessivamente polida
- Buzzwords sem evidências concretas (números, projetos, ferramentas)
- Estrutura perfeita demais, sem inconsistências naturais
- Falta de detalhes específicos verificáveis
- Padrões de frases típicas de LLM
- Vocabulário repetitivo e formal demais
Vereditos possíveis: "Provável humano" (<35), "Possível IA" (35-69), "Provável IA" (>=70).

## FORMATO DE SAÍDA (JSON OBRIGATÓRIO)
{{
  "candidato_nome": "nome completo extraído do currículo, ou '(sem nome)' se não encontrar",
  "scores_por_vaga": [
    {{
      "vaga_id": "string",
      "vaga_titulo": "string",
      "notas": {{
        "experiencia": 0-10,
        "tecnico": 0-10,
        "formacao": 0-10,
        "soft_skills": 0-10,
        "estabilidade": 0-10
      }},
      "score": 0.0-10.0,
      "classificacao": "Alta aderência|Média aderência|Baixa aderência"
    }}
  ],
  "vaga_recomendada": {{
    "id": "string",
    "titulo": "string",
    "score": 0.0-10.0,
    "justificativa": "string curta"
  }},
  "score_final": 0.0-10.0,
  "classificacao": "Alta aderência|Média aderência|Baixa aderência",
  "resumo_executivo": "máximo 5 linhas, objetivo",
  "pontos_fortes": ["item 1", "item 2", "..."],
  "pontos_atencao": ["item 1", "item 2", "..."],
  "recomendacao_final": "Aprovar para próxima etapa|Manter em banco|Reprovar",
  "deteccao_ia": {{
    "probabilidade": 0-100,
    "veredito": "Provável humano|Possível IA|Provável IA",
    "indicadores": ["item 1", "item 2", "..."]
  }}
}}

Responda APENAS com o JSON. Sem markdown, sem comentário."""


# Modelos a tentar em ordem: o configurado pelo usuário e fallbacks com cotas
# mais generosas na free-tier do Google AI Studio.
DEFAULT_MODEL = "gemini-2.5-flash"
FALLBACK_MODELS = ["gemini-2.5-flash-lite", "gemini-flash-lite-latest"]


class AnalyzerError(RuntimeError):
    def __init__(self, message: str, retry_after: float | None = None,
                 kind: str = "generic") -> None:
        super().__init__(message)
        self.retry_after = retry_after
        self.kind = kind


def _configure() -> None:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise AnalyzerError(
            "GEMINI_API_KEY não configurada. Edite o .env com sua chave do Google AI Studio.",
            kind="config",
        )
    genai.configure(api_key=api_key)


def _format_vagas(vagas: list[dict[str, Any]]) -> str:
    if not vagas:
        return "(Nenhuma vaga cadastrada — peça ao usuário para cadastrar antes de analisar.)"
    lines: list[str] = []
    for idx, vaga in enumerate(vagas, start=1):
        lines.append(f"### Vaga {idx}")
        lines.append(f"- id: {vaga['id']}")
        lines.append(f"- titulo: {vaga['titulo']}")
        if vaga.get("descricao"):
            lines.append(f"- descrição: {vaga['descricao']}")
        if vaga.get("requisitos"):
            lines.append(f"- requisitos: {vaga['requisitos']}")
        lines.append("")
    return "\n".join(lines).strip()


def _strip_json(text: str) -> str:
    text = text.strip()
    fenced = re.match(r"^```(?:json)?\s*(.*?)\s*```$", text, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()
    return text


def _retry_after_seconds(exc: Exception) -> float | None:
    """Extrai o retry_delay do erro de quota do Gemini, se houver."""
    msg = str(exc)
    m = re.search(r"retry_delay\s*{\s*seconds:\s*(\d+)", msg)
    if m:
        return float(m.group(1))
    m = re.search(r"Please retry in ([\d.]+)s", msg)
    if m:
        return float(m.group(1))
    return None


def _candidate_models() -> list[str]:
    primary = (os.environ.get("GEMINI_MODEL") or DEFAULT_MODEL).strip()
    chain = [primary]
    for fb in FALLBACK_MODELS:
        if fb not in chain:
            chain.append(fb)
    return chain


def _call_model(model_name: str, prompt: str) -> str:
    # temperature=0 + top_p=1 = saída quase determinística para o mesmo prompt.
    # max_output_tokens alto para suportar 50+ vagas no JSON de resposta.
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=SYSTEM_INSTRUCTIONS,
        generation_config={
            "temperature": 0.0,
            "top_p": 1.0,
            "max_output_tokens": 32768,
            "response_mime_type": "application/json",
        },
    )
    response = model.generate_content(prompt)
    return response.text or ""


def analisar_curriculo(
    curriculo_texto: str, vagas: list[dict[str, Any]]
) -> dict[str, Any]:
    if not curriculo_texto.strip():
        raise AnalyzerError("O currículo está vazio ou ilegível.", kind="input")

    _configure()
    prompt = PROMPT_TEMPLATE.format(
        vagas_block=_format_vagas(vagas),
        curriculo_texto=curriculo_texto[:30000],
    )

    last_quota_retry: float | None = None
    last_error: Exception | None = None

    for model_name in _candidate_models():
        try:
            raw = _call_model(model_name, prompt)
        except gax.ResourceExhausted as exc:
            last_error = exc
            last_quota_retry = _retry_after_seconds(exc) or last_quota_retry
            # Tenta o próximo modelo.
            continue
        except gax.GoogleAPIError as exc:
            raise AnalyzerError(
                f"Falha na API do Gemini ({exc.__class__.__name__}). "
                "Verifique a conexão e tente novamente.",
                kind="api",
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise AnalyzerError(
                "Erro inesperado ao chamar o Gemini. Tente novamente em alguns segundos.",
                kind="api",
            ) from exc

        cleaned = _strip_json(raw)
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            preview = cleaned[:240].replace("\n", " ")
            raise AnalyzerError(
                f"O modelo retornou um JSON inválido. Tente novamente. "
                f"Trecho recebido: \"{preview}…\"",
                kind="parse",
            ) from exc

        # Anota o modelo que efetivamente respondeu — útil para entender
        # variações de score (cada modelo pode pontuar diferente).
        if isinstance(data, dict):
            data["_model_used"] = model_name
        return data

    # Esgotou todos os modelos com ResourceExhausted.
    retry_msg = (
        f" Aguarde cerca de {int(last_quota_retry)}s e tente novamente."
        if last_quota_retry
        else " Aguarde alguns minutos e tente novamente."
    )
    raise AnalyzerError(
        "Limite gratuito do Gemini atingido em todos os modelos disponíveis."
        + retry_msg
        + " Para uso intenso, habilite billing no projeto do Google AI Studio.",
        retry_after=last_quota_retry,
        kind="quota",
    )
