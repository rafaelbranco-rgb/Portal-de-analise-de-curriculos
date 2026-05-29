# Deploy no Vercel

Este portal é um app Flask (Python) que roda no Vercel como *serverless
function*. Como o filesystem do Vercel é somente leitura, os dados (vagas,
análises e auditoria) ficam num PostgreSQL gerenciado (Neon ou Supabase, plano
grátis).

> ⚠️ **Use o painel do Vercel (https://vercel.com/new), NÃO o v0.dev.**
> O v0 é para apps React/Next gerados por IA e não faz o deploy correto deste
> backend Flask.

## 1. Banco PostgreSQL

Funciona com qualquer PostgreSQL. Monte a connection string no formato:

```
postgresql://USUARIO:SENHA@HOST:PORTA/BANCO?sslmode=MODO
```

- `sslmode=require` se o servidor aceita SSL (ex.: Neon/Supabase).
- `sslmode=disable` se o servidor **não** aceita SSL.

> Servidores gerenciados como **Neon** (https://neon.tech) oferecem Postgres
> grátis com SSL — basta copiar a connection string com `-pooler`.

## 2. Importar o projeto no Vercel

1. Vá em https://vercel.com/new.
2. Importe o repositório `Portal-de-analise-de-curriculos`.
3. **Não** mude o build — o `vercel.json` já configura tudo.

## 3. Configurar as variáveis de ambiente

Em **Settings → Environment Variables**, adicione:

| Nome             | Valor                                                        |
|------------------|--------------------------------------------------------------|
| `GEMINI_API_KEY` | sua chave do Google AI Studio                                |
| `GEMINI_MODEL`   | `gemini-2.5-pro` (ou `gemini-2.5-flash`, mais rápido/barato) |
| `DATABASE_URL`   | a connection string do Postgres (passo 1)                    |

Depois faça **Redeploy** para as variáveis valerem.

## 4. (Importante) Tempo máximo da função

A análise com o Gemini pode passar de 10s. Em **Settings → Functions**, aumente
o **Max Duration** para **60s** (máximo do plano Hobby). Se a análise der
timeout, é quase sempre isso.

## 5. Popular as vagas

O banco começa vazio. Rode localmente (só precisa de Python, sem dependências):

```bash
python seed_vagas.py https://SEU-APP.vercel.app
```

Isso cadastra todas as vagas via API, direto no banco de produção.

## Limitações conhecidas do serverless

- **Upload máximo ~4,5 MB** por requisição (limite do Vercel). Currículos em PDF
  costumam ser bem menores que isso.
- Cold start: a primeira requisição após inatividade é um pouco mais lenta.

## Rodando localmente (continua igual)

```bash
python -m venv .venv
.\.venv\Scripts\activate      # Windows
pip install -r requirements.txt
# crie um .env com GEMINI_API_KEY, GEMINI_MODEL e DATABASE_URL
python app.py
```
