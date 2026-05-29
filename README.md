# Portal de Análise de Currículos — Aions

Agente de IA que lê currículos, gera score ponderado pelos critérios do RH,
indica a vaga mais aderente do catálogo da empresa e ainda detecta se o
documento foi gerado por IA.

Visual no padrão **Liquid Glass** (dark navy + azul elétrico + dourado fosco),
inspirado no projeto `plano-intermitentes`.

---

## Stack

- **Backend:** Python 3.10+ · Flask · Gemini API (Google AI Studio)
- **Frontend:** HTML/CSS/JS puro (sem build, servido pelo Flask)
- **Storage:** JSON local (`data/jobs.json`)

---

## Como rodar

### 1. Criar e ativar ambiente virtual

```powershell
cd C:\Users\NOTECS-29\Documents\pneu
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 2. Instalar dependências

```powershell
pip install -r requirements.txt
```

### 3. Configurar a chave do Gemini

Copie o `.env.example` para `.env` e cole sua chave do
[Google AI Studio](https://aistudio.google.com/app/apikey):

```powershell
Copy-Item .env.example .env
```

Edite o `.env`:

```
GEMINI_API_KEY=AIza...sua_chave...
GEMINI_MODEL=gemini-1.5-pro
FLASK_PORT=5000
```

> O modelo padrão é `gemini-1.5-pro`. Para mais velocidade/menor custo, use
> `gemini-1.5-flash`.

### 4. Subir o servidor

```powershell
python app.py
```

Acesse <http://127.0.0.1:5000>.

---

## Fluxo de uso

1. **Vagas** → cadastre as vagas da empresa (título, descrição, requisitos).
2. **Analisar** → arraste o currículo (PDF/DOCX/TXT, até 8 MB).
3. O agente devolve:
   - Score final ponderado (0-10) e classificação (Alta / Média / Baixa).
   - Vaga recomendada com justificativa.
   - Resumo executivo, pontos fortes e pontos de atenção.
   - Probabilidade de o currículo ter sido gerado por IA + indicadores.
   - Notas individuais para **cada vaga** cadastrada.

---

## Critérios usados pelo agente

| Critério | Peso |
|---|---|
| Experiência relevante na função | 3 |
| Conhecimentos técnicos obrigatórios | 3 |
| Formação acadêmica | 2 |
| Soft skills evidenciadas | 1 |
| Estabilidade e progressão de carreira | 1 |

**Classificação:**
- 8.0 – 10.0 → Alta aderência
- 6.0 – 7.9 → Média aderência
- < 6.0 → Baixa aderência

---

## Estrutura

```
pneu/
├── app.py              # Flask app + rotas
├── analyzer.py         # Integração Gemini + prompt do RH
├── extractor.py        # PDF / DOCX / TXT → texto
├── jobs_store.py       # CRUD de vagas (JSON)
├── requirements.txt
├── .env.example
├── data/jobs.json      # criado em runtime
└── static/
    ├── index.html
    ├── css/styles.css
    └── js/
        ├── app.js
        └── tilt.js
```

---

## Endpoints

| Método | Rota | Função |
|---|---|---|
| GET | `/api/health` | Status + se a chave Gemini está configurada |
| GET | `/api/jobs` | Lista vagas |
| POST | `/api/jobs` | Cria vaga (`titulo`, `descricao`, `requisitos`) |
| PUT | `/api/jobs/<id>` | Atualiza vaga |
| DELETE | `/api/jobs/<id>` | Remove vaga |
| POST | `/api/analyze` | `multipart/form-data` com campo `curriculo` |

---

## Próximos passos sugeridos

- Histórico de análises (salvar resultados em SQLite).
- Login do RH (Flask-Login).
- Comparação entre múltiplos candidatos para a mesma vaga.
- Export PDF do laudo da análise.
- Anti-fraude: hash do arquivo + checagem contra base de currículos já vistos.
