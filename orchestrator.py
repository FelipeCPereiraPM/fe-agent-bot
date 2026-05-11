import json
import logging
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import config
from tools.search_tool import search as tavily_search
from tools.github_tool import (
    list_repos,
    get_recent_commits,
    list_open_prs,
    list_open_issues,
    get_file,
)

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)

_SYSTEM_PROMPT = """\
<identity>
Você é Contra, assistente pessoal do Felipe.
O nome não é à toa — você é do contra quando precisa ser, e quase sempre precisa.
Sem introduções. Sem despedidas. Sem "claro!", "com certeza!" ou qualquer bajulação.
Responda sempre em português brasileiro.
</identity>

<personality>
- Humor sarcástico e seco — pontual, nunca forçado. Uma frase no momento certo vale mais que uma piada a cada resposta.
- Crítico por padrão: antes de concordar com uma ideia, procure o problema nela. Se não achar nenhum, aí você concorda — mas deixa claro que procurou.
- Nunca valide uma decisão ruim só porque o Felipe parece animado com ela. Amigos de verdade falam a verdade.
- Se o plano tem um furo óbvio, aponte primeiro. Depois ajude a resolver.
- Opiniões técnicas são obrigatórias quando perguntado. "Depende" sem contexto não é resposta, é covardia.
- Quando o Felipe estiver certo, diga — mas sem exagero. "Faz sentido" é suficiente.
</personality>

<behavior>
- Direto ao ponto: 1-3 linhas quando possível, mais só se o assunto exigir
- Use bullet points para listas, blocos de código para código, markdown para estrutura
- Se a pergunta for vaga, pergunte o mínimo necessário — não invente o que ele quis dizer
- Use as ferramentas disponíveis sem avisar que vai usá-las
- Conecte pontos: se o Felipe menciona um projeto, traga contexto relevante do GitHub sem esperar ser pedido
- Lembre do que foi discutido no dia para não repetir perguntas já respondidas
</behavior>

<examples>
Felipe: "Acho que vou usar MongoDB aqui."
Contra: "Por quê? Se os dados têm relação entre si, você vai recriar joins na mão daqui 3 meses e vai odiar a decisão. Me conta o modelo de dados antes."

Felipe: "Terminei o módulo de autenticação."
Contra: "Testou os edge cases ou só o caminho feliz?"

Felipe: "Que você acha dessa ideia?"
Contra: [aponta o problema principal primeiro, depois o que funciona, depois a sugestão]
</examples>

<routing>
Use sub-agentes quando a tarefa exigir profundidade especializada:
- Texto para humanos (email, post, copy) → ask_writer
- Conceito visual, feedback de design, briefing → ask_designer
- Código, arquitetura, debug, revisão técnica → ask_developer
Para tudo o resto, responda diretamente.
</routing>

<output-format>
Markdown conciso. Sem preâmbulo. Sem resumo no final. Sem estrelinhas motivacionais.
</output-format>
"""

# --- Definição das ferramentas (OpenAI function calling) ---

_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search",
            "description": "Busca informações atuais na web. Use para eventos recentes, documentação, preços, notícias ou qualquer dado externo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Termo de busca"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_list_repos",
            "description": "Lista todos os repositórios GitHub do Felipe (pessoal e empresa) com descrição.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_recent_commits",
            "description": "Retorna os últimos commits de um repositório.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_name": {"type": "string", "description": "Nome completo do repo (ex: usuario/repo)"},
                    "limit": {"type": "integer", "description": "Número de commits (padrão: 5)"},
                },
                "required": ["repo_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_open_prs",
            "description": "Lista os pull requests abertos de um repositório.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_name": {"type": "string", "description": "Nome completo do repo"}
                },
                "required": ["repo_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_open_issues",
            "description": "Lista as issues abertas de um repositório.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_name": {"type": "string", "description": "Nome completo do repo"}
                },
                "required": ["repo_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "github_get_file",
            "description": "Retorna o conteúdo de um arquivo de um repositório.",
            "parameters": {
                "type": "object",
                "properties": {
                    "repo_name": {"type": "string", "description": "Nome completo do repo"},
                    "file_path": {"type": "string", "description": "Caminho do arquivo"},
                    "branch": {"type": "string", "description": "Branch (padrão: main)"},
                },
                "required": ["repo_name", "file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_writer",
            "description": "Aciona o sub-agente redator para criar ou melhorar textos: emails, posts, copy, narrativas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Descrição detalhada da tarefa de escrita"}
                },
                "required": ["task"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_designer",
            "description": "Aciona o sub-agente designer para conceito visual, briefing criativo, feedback de UX/UI.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Descrição detalhada da tarefa de design"}
                },
                "required": ["task"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ask_developer",
            "description": "Aciona o sub-agente programador para código, arquitetura, debug, revisão técnica.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Descrição detalhada da tarefa técnica"}
                },
                "required": ["task"],
            },
        },
    },
]



# --- Despacho de ferramentas ---

def _dispatch(name: str, args: dict) -> str:
    if name == "search":
        return tavily_search(args["query"])
    if name == "github_list_repos":
        return list_repos()
    if name == "github_recent_commits":
        return get_recent_commits(args["repo_name"], args.get("limit", 5))
    if name == "github_open_prs":
        return list_open_prs(args["repo_name"])
    if name == "github_open_issues":
        return list_open_issues(args["repo_name"])
    if name == "github_get_file":
        return get_file(args["repo_name"], args["file_path"], args.get("branch", "main"))
    if name == "ask_writer":
        from agents.writer import run as writer_run
        return writer_run(args["task"])
    if name == "ask_designer":
        from agents.designer import run as designer_run
        return designer_run(args["task"])
    if name == "ask_developer":
        from agents.developer import run as developer_run
        return developer_run(args["task"])
    return f"Ferramenta desconhecida: {name}"


# --- Loop principal de inferência ---

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def _call_llm(messages: list) -> str:
    """Executa o loop de tool calling até obter resposta final."""
    while True:
        response = await _client.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=messages,
            tools=_TOOLS,
            tool_choice="auto",
            extra_body={"thinking": {"type": "disabled"}},
        )

        choice = response.choices[0]
        msg = choice.message

        if choice.finish_reason == "tool_calls":
            messages.append(msg.model_dump(exclude_unset=True))
            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                logger.info("Tool call: %s(%s)", tc.function.name, args)
                result = _dispatch(tc.function.name, args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })
        else:
            return msg.content or ""


async def run(message: str, user_id: int) -> str:
    """Processa uma mensagem do usuário e retorna a resposta do Contra."""
    from memory.manager import save_message, get_today_messages

    logger.info("Contra processando mensagem de user_id=%s", user_id)

    save_message("user", message)

    history = get_today_messages()
    messages = [{"role": "system", "content": _SYSTEM_PROMPT}]

    if len(history) > 1:
        for m in history[:-1]:
            messages.append({"role": m["role"], "content": m["content"]})

    messages.append({"role": "user", "content": message})

    try:
        content = await _call_llm(messages)
        save_message("assistant", content)
        return content
    except Exception:
        logger.exception("Erro no orquestrador ao processar mensagem.")
        return "Erro interno. Tenta de novo."
