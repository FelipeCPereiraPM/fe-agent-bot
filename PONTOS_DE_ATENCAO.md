# Pontos de Atenção — Projeto Fe-Agent

Relatório de riscos e alertas identificados na revisão inicial do arquivo `CLAUDE.md`.

## 1. Segurança e Acesso (Crítico)
*   **Problema:** O bot está configurado como "Single User", mas não há menção a um filtro de `USER_ID`.
*   **Risco:** Se o bot for descoberto, terceiros podem consumir créditos da API e acessar dados privados (Agenda/GitHub).
*   **Ação:** Adicionar `AUTHORIZED_USER_ID` no `.env` e implementar middleware de validação no `main.py`.

## 2. Limitações de API (Performance)
*   **Problema:** Uso do DeepSeek como LLM com loop de tool calling próprio — múltiplas chamadas por mensagem (orquestrador + sub-agentes + tools).
*   **Risco:** Rate limits da API do DeepSeek em fluxos que exigem muitas iterações. Pode causar timeouts no polling do Telegram.
*   **Ação:** Implementar lógica de retry robusta com backoff exponencial em todas as chamadas ao DeepSeek.

## 3. Gestão de Tokens (Google OAuth2)
*   **Problema:** Necessidade de `refresh_token` manual no `.env`.
*   **Risco:** Dificuldade de renovação em ambiente headless (Railway). Se o token expirar e o refresh falhar, o bot para de funcionar.
*   **Ação:** Criar um script `tools/auth_google.py` para gerar o token inicial localmente e validar o fluxo de auto-refresh.

## 4. Integração n8n (Escopo)
*   **Problema:** A definição de "Read-only" para n8n é vaga.
*   **Risco:** Implementação de uma tool genérica demais que não traz utilidade real ou que tenta parsear retornos complexos sem estrutura.
*   **Ação:** Definir quais workflows específicos serão consultados e qual o formato esperado de resposta.

## 5. Estabilidade do Loop de Tool Calling (AsyncOpenAI)
*   **Problema:** O loop de tool calling é implementado diretamente no projeto, sem abstração de framework (Agno foi removido por ser ponto de falha).
*   **Risco:** Erros no loop (ex: tool call sem resposta correspondente, resposta malformada do modelo) podem travar a conversa ou gerar loops infinitos.
*   **Ação:** Garantir condição de saída clara no loop (ausência de `tool_calls` na resposta), tratar exceções em cada execução de tool e logar todas as iterações para facilitar debug.

---
**Data da revisão:** 11/05/2026
**Status:** Aguardando correções para início do desenvolvimento.
