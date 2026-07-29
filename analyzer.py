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

- A "vaga_recomendada" deve ser SEMPRE a de maior score real, NÃO um chute
- Considere a LOCALIDADE da vaga vs do candidato: se vagas e CV são de cidades
  diferentes, NÃO descarte automaticamente, mas registre em pontos de atenção

{detalhe_block}

## VAGAS DISPONÍVEIS
{vagas_block}

## CURRÍCULO DO CANDIDATO
\"\"\"
{curriculo_texto}
\"\"\"
{pcd_block}
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
      "classificacao": "Alta aderência|Média aderência|Baixa aderência",
      "resumo_executivo": "APENAS nas vagas detalhadas (ver CONTROLE DE TAMANHO): 1-2 linhas sobre a aderência A ESTA vaga",
      "pontos_fortes": ["APENAS nas vagas detalhadas: aspectos que favorecem o candidato NESTA vaga"],
      "pontos_atencao": ["APENAS nas vagas detalhadas: lacunas/riscos do candidato NESTA vaga"]
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
  }},
  "analise_pcd": {{
    "is_pcd": true|false,
    "indicador": "sem_interferencia|compativel_com_adaptacoes|requer_avaliacao_ocupacional|nao_informado",
    "titulo": "rótulo curto e formal do indicador (ex.: 'Sem interferência prevista')",
    "parecer": "parecer formal, técnico e respeitoso (2-4 linhas) sobre a compatibilidade entre a condição declarada e as ATRIBUIÇÕES da vaga recomendada",
    "condicao_declarada": "resumo da especificação/laudo, ou 'Não informado'",
    "pontos_atencao": ["barreira/condição do ambiente ou da função que merece atenção para garantir um trabalho seguro e produtivo — NUNCA um defeito da pessoa"],
    "adaptacoes_sugeridas": ["adaptação razoável 1", "..."],
    "fundamentacao": "em que se baseou (laudo/especificação x demandas da função)"
  }}
}}

Responda APENAS com o JSON. Sem markdown, sem comentário."""


# Controle de tamanho da resposta. Com 50+ vagas, pedir resumo + pontos fortes +
# pontos de atenção para TODAS elas estoura o limite de tokens de saída e o JSON
# volta cortado no meio (erro "JSON inválido"). Por isso o detalhe por vaga fica
# restrito às melhores; as demais devolvem só nota/score.
DETALHE_COMPLETO = """## CONTROLE DE TAMANHO DA RESPOSTA (regra obrigatória)
Sua resposta tem um LIMITE de tamanho. Se você exceder, ela é cortada no meio e
TODO o trabalho é perdido. Portanto:
- Pontue TODAS as vagas: nenhuma pode faltar em "scores_por_vaga".
- Detalhe APENAS as {top_n} vagas de MAIOR score. Nessas, preencha
  "resumo_executivo" (máximo 2 linhas), "pontos_fortes" e "pontos_atencao"
  (máximo 3 itens de até 140 caracteres cada).
- Para TODAS as outras vagas devolva SOMENTE os campos "vaga_id", "vaga_titulo",
  "notas", "score" e "classificacao". OMITA "resumo_executivo", "pontos_fortes"
  e "pontos_atencao" — não os devolva vazios, simplesmente não os inclua.
- Nunca repita a descrição da vaga nem trechos do currículo na resposta.
"""

DETALHE_ENXUTO = """## CONTROLE DE TAMANHO DA RESPOSTA — MODO ENXUTO (regra obrigatória)
A tentativa anterior estourou o limite e foi cortada. Agora seja radicalmente
mais econômico:
- Pontue TODAS as vagas, mas para CADA UMA devolva SOMENTE os campos "vaga_id",
  "vaga_titulo", "notas", "score" e "classificacao".
- NÃO inclua "resumo_executivo", "pontos_fortes" nem "pontos_atencao" dentro de
  "scores_por_vaga" para NENHUMA vaga.
- Nos campos globais (fora de "scores_por_vaga"), mantenha a análise completa,
  mas objetiva: "resumo_executivo" com até 4 linhas, "pontos_fortes" e
  "pontos_atencao" com até 4 itens curtos cada.
- Nunca repita a descrição da vaga nem trechos do currículo na resposta.
"""


def _detalhe_block(modo: str) -> str:
    if modo == "enxuto":
        return DETALHE_ENXUTO
    try:
        top_n = max(1, int(os.environ.get("ANALISE_TOP_DETALHE", "8")))
    except ValueError:
        top_n = 8
    return DETALHE_COMPLETO.format(top_n=top_n)


PCD_BLOCK_TEMPLATE = """
## ANÁLISE DE PCD (Pessoa com Deficiência) — OBRIGATÓRIA E CONSULTIVA
O candidato declarou condição de PCD. Avalie a COMPATIBILIDADE entre a condição
e as ATRIBUIÇÕES da vaga recomendada, à luz da Lei Brasileira de Inclusão
(Lei 13.146/2015) e da Lei de Cotas (Lei 8.213/91).

REGRAS INEGOCIÁVEIS:
- Esta análise é CONSULTIVA. Ela NÃO pode alterar `score_final`, `scores_por_vaga`,
  `classificacao` nem `recomendacao_final`. Avalie o mérito profissional EXATAMENTE
  como faria com qualquer candidato — a condição PCD não soma nem subtrai pontos.
- NUNCA recomende reprovar, desclassificar ou rebaixar o candidato por causa da
  deficiência. Isso é discriminação e é vedado.
- Raciocine em termos de ADAPTAÇÕES RAZOÁVEIS e acessibilidade, jamais de
  "incapacidade" do candidato. Linguagem formal, técnica e respeitosa.

PONTOS DE ATENÇÃO (campo `pontos_atencao`) — REGRAS DE ENQUADRAMENTO:
- Liste pontos que o RH deve observar para que a pessoa trabalhe com segurança e
  produtividade. Enquadre SEMPRE como BARREIRA DO AMBIENTE/DA FUNÇÃO a resolver,
  nunca como falha, fraqueza ou "desvantagem" da pessoa.
- Errado: "candidato não consegue X". Certo: "a função exige X em escadas sem
  acesso adaptado; avaliar adequação do posto".
- Vincule cada ponto, quando possível, a uma adaptação em `adaptacoes_sugeridas`.
- Se não houver pontos relevantes, devolva lista vazia. NÃO invente desvantagens
  para preencher.

Classifique `indicador` assim:
- "sem_interferencia": a condição não impacta as atribuições essenciais da função.
- "compativel_com_adaptacoes": a função é exercível com adaptações razoáveis —
  liste-as em `adaptacoes_sugeridas`.
- "requer_avaliacao_ocupacional": há, no laudo, restrição potencialmente relevante
  às demandas físicas/ambientais da função; encaminhar ao SESMT / medicina
  ocupacional antes de qualquer decisão. (Isto NÃO é reprovação.)

DADOS DECLARADOS NO FORMULÁRIO:
- PCD: {pcd}
- Especificação: {especificacao}
- Laudo atualizado (texto extraído, pode estar vazio ou parcial):
\"\"\"
{laudo}
\"\"\"
"""


def _build_pcd_block(pcd_context: dict[str, Any] | None) -> str:
    """Monta o trecho de PCD do prompt; vazio quando não há contexto de PCD."""
    if not pcd_context:
        return (
            "\n## ANÁLISE DE PCD\n"
            "Não há informação de PCD para este candidato. No JSON, preencha "
            '`analise_pcd` com {"is_pcd": false, "indicador": "nao_informado", '
            '"titulo": "Não informado", "parecer": "Não informado", '
            '"condicao_declarada": "Não informado", "adaptacoes_sugeridas": [], '
            '"fundamentacao": ""}.\n'
        )
    laudo = (pcd_context.get("laudo_texto") or "").strip()
    return PCD_BLOCK_TEMPLATE.format(
        pcd=pcd_context.get("pcd") or "Não informado",
        especificacao=pcd_context.get("especificacao") or "Não informado",
        laudo=(laudo[:12000] if laudo else "(laudo não anexado ou ilegível)"),
    )


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


# Teto de tokens de saída. Nos modelos 2.5 o "raciocínio interno" do modelo
# consome o MESMO orçamento da resposta visível, então um teto apertado corta o
# JSON no meio. 65536 é o máximo aceito pelo gemini-2.5-pro/flash.
MAX_OUTPUT_TOKENS = 65536


def _extract_text_and_finish(response: Any) -> tuple[str, str]:
    """Devolve (texto, motivo_de_parada) sem estourar quando não há texto.

    ``response.text`` levanta exceção se o candidato não tiver parte textual
    (acontece justamente quando a geração é interrompida). Aqui montamos o texto
    a partir das partes e lemos o ``finish_reason`` para saber se foi corte por
    limite de tokens (``MAX_TOKENS``).
    """
    finish = ""
    chunks: list[str] = []
    try:
        candidates = list(getattr(response, "candidates", None) or [])
    except Exception:  # noqa: BLE001
        candidates = []
    if candidates:
        cand = candidates[0]
        reason = getattr(cand, "finish_reason", None)
        if reason is not None:
            finish = getattr(reason, "name", None) or str(reason)
        parts = getattr(getattr(cand, "content", None), "parts", None) or []
        for part in parts:
            text = getattr(part, "text", "") or ""
            if text:
                chunks.append(text)
    return "".join(chunks), finish


def _call_model(model_name: str, prompt: str) -> tuple[str, str]:
    # temperature=0 + top_p=1 = saída quase determinística para o mesmo prompt.
    model = genai.GenerativeModel(
        model_name=model_name,
        system_instruction=SYSTEM_INSTRUCTIONS,
        generation_config={
            "temperature": 0.0,
            "top_p": 1.0,
            "max_output_tokens": MAX_OUTPUT_TOKENS,
            "response_mime_type": "application/json",
        },
    )
    return _extract_text_and_finish(model.generate_content(prompt))


def analisar_curriculo(
    curriculo_texto: str,
    vagas: list[dict[str, Any]],
    pcd_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not curriculo_texto.strip():
        raise AnalyzerError("O currículo está vazio ou ilegível.", kind="input")

    _configure()
    vagas_block = _format_vagas(vagas)
    pcd_block = _build_pcd_block(pcd_context)
    curriculo = curriculo_texto[:30000]

    def _prompt(modo: str) -> str:
        return PROMPT_TEMPLATE.format(
            vagas_block=vagas_block,
            curriculo_texto=curriculo,
            pcd_block=pcd_block,
            detalhe_block=_detalhe_block(modo),
        )

    last_quota_retry: float | None = None
    ultimo_motivo = ""    # finish_reason da última resposta ilegível
    ultimo_preview = ""

    for model_name in _candidate_models():
        sem_cota = False
        # 1ª tentativa: detalhe nas melhores vagas. Se a resposta vier cortada,
        # 2ª tentativa no mesmo modelo em modo enxuto (resposta bem menor).
        for modo in ("completo", "enxuto"):
            try:
                raw, motivo_parada = _call_model(model_name, _prompt(modo))
            except gax.ResourceExhausted as exc:
                last_quota_retry = _retry_after_seconds(exc) or last_quota_retry
                sem_cota = True
                break  # tenta o próximo modelo
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
            except json.JSONDecodeError:
                # Resposta interrompida no meio (normalmente motivo MAX_TOKENS).
                ultimo_motivo = motivo_parada or "desconhecido"
                ultimo_preview = cleaned[:240].replace("\n", " ")
                continue

            # Anota o modelo que efetivamente respondeu — útil para entender
            # variações de score (cada modelo pode pontuar diferente).
            if isinstance(data, dict):
                data["_model_used"] = model_name
                data["_modo_resposta"] = modo
            return data

        if sem_cota:
            continue

        # Os dois modos falharam por formato: reenviar não resolve.
        raise AnalyzerError(
            "A resposta da análise veio incompleta e não pôde ser lida "
            f"(motivo da interrupção: {ultimo_motivo}). Este currículo precisa de "
            f"avaliação manual. Trecho recebido: \"{ultimo_preview}…\"",
            kind="parse",
        )

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
