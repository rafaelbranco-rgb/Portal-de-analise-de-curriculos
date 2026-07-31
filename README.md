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

## Acesso (login obrigatório)

O portal é confidencial: nada abre sem login. Cada pessoa tem e-mail e senha
próprios e todos têm o mesmo nível de acesso (inclusive para cadastrar e
remover usuários, em **Opções → Acesso e usuários**).

- O **primeiro** usuário nasce das variáveis `PORTAL_ADMIN_EMAIL` e
  `PORTAL_ADMIN_SENHA` — válidas só enquanto o banco não tem nenhum usuário.
- A sessão dura 12 h de inatividade e o cookie é assinado com `SECRET_KEY`.
- 5 senhas erradas bloqueiam a conta por 5 minutos.
- Entradas, saídas, tentativas recusadas e cada abertura de currículo ficam
  registradas na **Auditoria**, com o e-mail de quem fez.
- Automações (webhook do Monday, `/api/triagem`) seguem com token próprio;
  scripts como o `seed_vagas.py` entram com o header `X-API-Key`
  (= `TRIAGEM_API_KEY`).

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
4. O **currículo original fica anexado ao laudo** do candidato: dá para ver na
   própria página (PDF/TXT), abrir em outra aba ou baixar. Vale tanto para o
   upload manual quanto para os currículos que chegam pelo Monday. Análises
   feitas antes desta versão não têm o arquivo guardado.

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
├── app.py              # Flask app + rotas
├── auth.py             # login por sessão + rotas de usuários
├── users_store.py      # usuários (senha em hash)
├── analyzer.py         # Integração Gemini + prompt do RH
├── extractor.py        # PDF / DOCX / TXT → texto
├── jobs_store.py       # CRUD de vagas
├── analyses_store.py   # histórico + cópia do currículo
├── audit_log.py        # trilha de auditoria
├── db.py               # conexão e schema do Postgres
├── monday_client.py    # triagem/captação no monday.com
├── requirements.txt
├── .env.example
├── templates/          # servidos pelo Flask (fora da pasta pública)
│   ├── app.html        # portal (só abre logado)
│   └── login.html      # tela de login
└── static/             # público: sem dado de candidato
    ├── css/styles.css
    └── js/
        ├── app.js
        └── tilt.js
```

---

## Endpoints

Tudo exige sessão (login) ou o header `X-API-Key`, menos o que está marcado
como *livre*.

| Método | Rota | Função |
|---|---|---|
| GET | `/login` | Tela de login (*livre*) |
| GET | `/api/auth/status` | Se está logado / se falta criar o 1º usuário (*livre*) |
| POST | `/api/auth/login` | Entra (`email`, `senha`) (*livre*) |
| POST | `/api/auth/logout` | Sai |
| GET | `/api/auth/me` | Usuário da sessão |
| POST | `/api/auth/senha` | Troca a própria senha (`senha_atual`, `nova_senha`) |
| GET | `/api/users` | Lista usuários |
| POST | `/api/users` | Cria usuário (`nome`, `email`, `senha`) |
| DELETE | `/api/users/<id>` | Remove usuário |
| POST | `/api/users/<id>/senha` | Redefine a senha de outro usuário |
| GET | `/api/health` | Status + se a chave Gemini está configurada |
| GET | `/api/jobs` | Lista vagas |
| POST | `/api/jobs` | Cria vaga (`titulo`, `descricao`, `requisitos`) |
| PUT | `/api/jobs/<id>` | Atualiza vaga |
| DELETE | `/api/jobs/<id>` | Remove vaga |
| POST | `/api/analyze` | `multipart/form-data` com campo `curriculo` |
| GET | `/api/analyses/<id>/curriculo` | Currículo guardado (`?download=1` baixa) |
| POST | `/api/triagem` | Triagem para automação (header `X-API-Key`) |
| POST | `/api/monday-webhook` | Webhook do Monday (`?token=`) (*livre*) |

---

## Próximos passos sugeridos

- Comparação entre múltiplos candidatos para a mesma vaga.
- Export PDF do laudo da análise.
- Anti-fraude: hash do arquivo + checagem contra base de currículos já vistos.
