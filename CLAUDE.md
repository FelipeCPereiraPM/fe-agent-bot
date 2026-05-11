# Fe-Agent — Assistente Pessoal via Telegram

## Visão geral

Agente orquestrador pessoal do Fe, acessível via Telegram. Analisa contexto real dos projetos, debate ideias, organiza planos e aciona sub-agentes especializados. Uso exclusivo (single user).

---

## Stack

| Camada | Tecnologia |
|---|---|
| Interface | Telegram — `python-telegram-bot` |
| Orquestrador | Custom (OpenAI SDK + Manual Function Calling) |
| LLM | DeepSeek Chat (via OpenAI SDK) |
| Memória | PostgreSQL (Railway) |
| Web search | Tavily API |
| GitHub | PyGithub — read-only |
| Google Agenda | Google Calendar API + OAuth2 — read/write, sem delete |
| n8n | REST API — read-only |
| Hospedagem | Railway — serviço dedicado (separado do n8n) |

---

## Arquitetura

```
Telegram (Felipe)
    ↓
Orquestrador (Custom Python + OpenAI SDK + DeepSeek)
    ↓
    ├── Responde direto
    ├── Busca contexto → GitHub / Google Agenda / n8n / Tavily
    └── Aciona sub-agente → Redator / Designer / Programador (OpenAI Call)
                    ↓
        Resposta consolidada → Telegram
```


---

## Estrutura de pastas

```
fe-agent/
├── main.py              # Inicia o bot Telegram (com validação de USER_ID)
├── orchestrator.py      # Agente principal (Agno) — LLM decide roteamento
├── scheduler.py         # Geração automática do diário (APScheduler)
├── agents/
│   ├── writer.py        # Sub-agente redator
│   ├── designer.py      # Sub-agente designer
│   └── developer.py     # Sub-agente programador
├── tools/
│   ├── github_tool.py
│   ├── calendar_tool.py
│   ├── search_tool.py
│   └── auth_google.py   # Gera refresh token localmente (rodar antes do deploy)
├── skills/
│   └── diary.py         # Skill: gera diário de bordo do dia e salva no PostgreSQL
├── memory/
│   └── manager.py       # PostgreSQL: sessão diária + diários salvos (valida conexão no startup)
├── config.py
├── .env
├── .env.example
└── requirements.txt     # Versões pinadas (incluindo Agno)
```

---

## Variáveis de ambiente (.env)

```env
TELEGRAM_BOT_TOKEN=
AUTHORIZED_USER_ID=        # Seu Telegram user ID — obtido via @userinfobot

# LLM via OpenRouter
OPENROUTER_API_KEY=
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free

TAVILY_API_KEY=

GITHUB_TOKEN_PERSONAL=
GITHUB_TOKEN_COMPANY=
GITHUB_REPOS_PERSONAL=repo1,repo2
GITHUB_REPOS_COMPANY=org/repo1,org/repo2

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REFRESH_TOKEN=      # Gerado localmente via tools/auth_google.py antes do deploy

DATABASE_URL=              # PostgreSQL no Railway — provisionar antes de iniciar o desenvolvimento

DIARY_HOUR=21              # Hora local para geração automática do diário (padrão: 21h)
DIARY_MINUTE=0
```

---

## Memória

**Curto prazo (sessão do dia):**
- Histórico da conversa mantido em memória durante o dia
- Uma sessão = um dia (reset automático à meia-noite ou ao gerar o diário)

**Longo prazo (diário de bordo):**
- Skill agendada gera automaticamente um resumo estruturado ao final do dia
- Formato markdown com: decisões tomadas, tarefas, ideias, contexto relevante
- Salvo no PostgreSQL (tabela `diarios`, campo `date` + `content` em markdown)
- Consultas futuras usam o diário como contexto — não o histórico bruto

**Gestão via Telegram:**
- `/diario` — força geração imediata do diário do dia
- `/diarios` — lista diários salvos (por data)
- `/diario [data]` — exibe diário de uma data específica (ex: `/diario 2026-05-10`)

---

## Sub-agentes

Chamadas ao OpenRouter com system prompts distintos — não são serviços separados.

| Sub-agente | Responsabilidade |
|---|---|
| Redator | Textos, emails, copy, narrativa |
| Designer | Conceito visual, briefing, feedback de UX |
| Programador | Arquitetura, código, debug, revisão técnica |

---

## Integrações — regras de acesso

| Integração | Permitido | Bloqueado |
|---|---|---|
| GitHub pessoal | Leitura | Qualquer escrita |
| GitHub empresa | Leitura | Qualquer escrita |
| Google Agenda | Leitura + criação/edição | Delete |
| n8n | Leitura | Qualquer alteração |

---

## Roadmap

### MVP (v1)
- [ ] Bot Telegram (polling) com validação de `AUTHORIZED_USER_ID`
- [ ] Orquestrador Agno + OpenRouter (LLM decide roteamento)
- [ ] Memória: sessão diária + diário de bordo automático no PostgreSQL
- [ ] Skill agendada: geração do diário ao final do dia (APScheduler ou Agno scheduler)
- [ ] Tools: GitHub (read-only), Google Agenda (read/write), Tavily
- [ ] Sub-agentes: redator, designer, programador
- [ ] Deploy no Railway
- [ ] **Pré-requisito:** provisionar PostgreSQL no Railway antes de começar a Fase 2 de implementação

### Fase 2
- [ ] Integração n8n (read-only) — escopo a definir
- [ ] Exportar diários para Obsidian (quando vault tiver sync)
- [ ] MCPs para sub-agentes agirem
- [ ] Webhook em vez de polling

---

## Padrões

- Credenciais sempre em `.env`
- `try/except` em toda chamada externa
- Logging com `logging`, não `print`
- Uma função = uma responsabilidade
- Testar cada tool isoladamente antes do deploy
- `main.py` rejeita silenciosamente (log) qualquer mensagem de user ID não autorizado
- Retry com backoff exponencial em toda chamada ao LLM (OpenRouter free tier tem rate limits severos)
- System prompts dos sub-agentes em formato XML com "Cable Mode" (sem cortesias, respostas diretas)
- `memory/manager.py` valida a conexão PostgreSQL antes de iniciar o loop do Telegram

---

## Setup inicial

1. Criar bot no Telegram via @BotFather → salvar `TELEGRAM_BOT_TOKEN`
2. Pegar seu Telegram User ID via @userinfobot → salvar `AUTHORIZED_USER_ID`
3. Criar conta no OpenRouter → gerar API key
4. Criar conta Tavily → gerar API key
5. Criar GitHub tokens (read-only) para repos definidos
6. Google Cloud → habilitar Calendar API → criar credenciais OAuth2 → rodar `tools/auth_google.py` localmente → salvar `GOOGLE_REFRESH_TOKEN`
7. Provisionar PostgreSQL no Railway → salvar `DATABASE_URL`
8. Definir quais workflows n8n serão consultados → atualizar `N8N_WORKFLOWS`
9. Pinar versão do Agno no `requirements.txt` (`pip show agno` ou verificar PyPI)
10. Configurar `.env` → testar tools isoladamente → deploy Railway

---

## Riscos

| Risco | Mitigação |
|---|---|
| Bot descoberto por terceiros | `AUTHORIZED_USER_ID` no middleware do `main.py` — rejeita silenciosamente |
| Google OAuth expira em headless | `tools/auth_google.py` gera token localmente; refresh automático no `calendar_tool.py` |
| OpenRouter rate limit (free tier) | Retry com backoff exponencial no orchestrator e sub-agentes |
| Repos da empresa expostos | Token mínimo, repos explícitos no `.env` |
| Agno update quebra schema PostgreSQL | Versão pinada no `requirements.txt`; `manager.py` valida conexão no startup |
| Memória crescendo | Gestão de sessões via Telegram (`/sessions`, `/delete`) |
