# Railway Setup — Fe-Agent

Guia passo a passo para configurar o projeto e o PostgreSQL no Railway.

---

## 1. Criar conta e projeto

1. Acesse [railway.app](https://railway.app) e faça login (pode usar GitHub)
2. No dashboard, clique em **New Project**
3. Selecione **Empty Project**
4. Renomeie o projeto para `fe-agent` (clique no nome padrão no topo)

---

## 2. Adicionar o PostgreSQL

1. Dentro do projeto, clique em **+ New**
2. Selecione **Database** → **Add PostgreSQL**
3. O Railway vai provisionar o banco automaticamente (leva ~30 segundos)
4. Clique no serviço PostgreSQL que apareceu
5. Vá na aba **Variables**
6. Copie o valor de `DATABASE_URL` — você vai precisar dele no `.env`

> O formato será algo como:  
> `postgresql://postgres:senha@host.railway.internal:5432/railway`

---

## 3. Criar o serviço do bot

1. Clique em **+ New** novamente
2. Selecione **GitHub Repo** (recomendado) ou **Empty Service**

### Se usar GitHub Repo:
- Autorize o Railway a acessar seu GitHub
- Selecione o repositório do fe-agent
- O Railway vai detectar o Python e configurar o build automaticamente

### Se usar Empty Service (para testar antes de subir o código):
- Selecione **Empty Service**
- Renomeie para `fe-agent-bot`
- O deploy vai ser feito depois via CLI ou GitHub

---

## 4. Configurar as variáveis de ambiente do bot

1. Clique no serviço `fe-agent-bot`
2. Vá na aba **Variables**
3. Clique em **+ New Variable** e adicione cada variável do `.env`:

```
TELEGRAM_BOT_TOKEN        = seu_token_aqui
AUTHORIZED_USER_ID        = seu_user_id_aqui
DEEPSEEK_API_KEY          = sua_chave_aqui
DEEPSEEK_MODEL            = deepseek-chat
TAVILY_API_KEY            = sua_chave_aqui
GITHUB_TOKEN_PERSONAL     = seu_token_aqui
GITHUB_TOKEN_COMPANY      = seu_token_aqui
GITHUB_REPOS_PERSONAL     = repo1,repo2
GITHUB_REPOS_COMPANY      = org/repo1,org/repo2
GOOGLE_CLIENT_ID          = seu_client_id
GOOGLE_CLIENT_SECRET      = seu_client_secret
GOOGLE_REFRESH_TOKEN      = seu_refresh_token
DIARY_HOUR                = 21
DIARY_MINUTE              = 0
```

4. Para o `DATABASE_URL`, ao invés de copiar manualmente, clique em **+ New Variable** → **Add Reference** → selecione o serviço PostgreSQL → selecione `DATABASE_URL`

> Isso cria uma referência dinâmica. Se o banco for recriado, o valor atualiza automaticamente.

---

## 5. Configurar o comando de start

1. No serviço `fe-agent-bot`, vá em **Settings**
2. Em **Start Command**, defina:
   ```
   python main.py
   ```
3. Em **Root Directory**, deixe em branco (ou `/` se o código estiver na raiz)

---

## 6. Configurar o Nixpacks (build)

O Railway usa Nixpacks para buildar Python automaticamente. Para garantir que as dependências sejam instaladas corretamente:

1. Certifique-se de que o `requirements.txt` está na raiz do projeto
2. O Railway vai rodar `pip install -r requirements.txt` automaticamente
3. Se precisar de uma versão específica de Python, crie um arquivo `runtime.txt` na raiz:
   ```
   python-3.11
   ```

---

## 7. Configurar o domínio (opcional para webhook futuro)

O bot usa polling no MVP, então domínio não é obrigatório agora. Mas para a Fase 2 (webhook):

1. No serviço `fe-agent-bot`, vá em **Settings** → **Networking**
2. Clique em **Generate Domain**
3. Anote o domínio gerado — vai ser usado na configuração do webhook do Telegram

---

## 8. Verificar a conexão com o PostgreSQL

Antes do primeiro deploy, valide que o banco está acessível:

1. No serviço PostgreSQL, vá na aba **Data** → **Query**
2. Execute:
   ```sql
   SELECT version();
   ```
3. Se retornar a versão do PostgreSQL, está funcionando

---

## 9. Estrutura final do projeto no Railway

```
fe-agent (projeto)
├── PostgreSQL          ← banco de dados
└── fe-agent-bot        ← serviço do bot Python
```

Os dois serviços ficam na mesma rede interna do Railway, então a conexão entre eles é direta e sem latência extra.

---

## 10. Deploy

### Via GitHub (automático):
- Qualquer push para a branch configurada (geralmente `main`) dispara um novo deploy
- Acompanhe os logs em **Deployments** → clique no deploy em andamento

### Via Railway CLI (manual):
```bash
# Instalar a CLI
npm install -g @railway/cli

# Login
railway login

# Linkar ao projeto
railway link

# Deploy
railway up
```

---

## Checklist final

- [ ] Conta Railway criada
- [ ] Projeto `fe-agent` criado
- [ ] PostgreSQL provisionado
- [ ] `DATABASE_URL` copiado para o `.env` local
- [ ] Serviço `fe-agent-bot` criado
- [ ] Variáveis de ambiente configuradas no Railway
- [ ] Start command definido (`python main.py`)
- [ ] `runtime.txt` criado com versão do Python
- [ ] Conexão com PostgreSQL validada via Query
