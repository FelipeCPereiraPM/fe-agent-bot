import logging
from agno.agent import Agent
from agno.models.openai import OpenAILike
from agno.tools import tool

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

<tools_available>
- search: busca na web via Tavily — use para qualquer informação atual ou externa
- github_list_repos: lista os repositórios do Felipe (pessoal + empresa)
- github_recent_commits: últimos commits de um repositório específico
- github_open_prs: pull requests abertos de um repositório
- github_open_issues: issues abertas de um repositório
- github_get_file: conteúdo de um arquivo específico de um repositório
- ask_writer: aciona o sub-agente redator para textos, emails, copy
- ask_designer: aciona o sub-agente designer para conceito visual, briefing, UX
- ask_developer: aciona o sub-agente programador para código, arquitetura, debug
</tools_available>

<routing>
Use sub-agentes quando a tarefa exigir profundidade especializada:
- Texto para humanos (email, post, copy) → ask_writer
- Conceito visual, feedback de design, briefing → ask_designer
- Código, arquitetura, debug, revisão técnica → ask_developer
Para tudo o resto, responda diretamente — você não precisa de ajuda para perguntas simples.
</routing>

<output-format>
Markdown conciso. Sem preâmbulo. Sem resumo no final. Sem estrelinhas motivacionais.
</output-format>
"""


def _make_model() -> OpenAILike:
    return OpenAILike(
        id=config.DEEPSEEK_MODEL,
        api_key=config.DEEPSEEK_API_KEY,
        base_url=config.DEEPSEEK_BASE_URL,
        # Desabilita o thinking mode do DeepSeek para evitar o erro 400:
        # "The `reasoning_content` in the thinking mode must be passed back
        # to the API." O Agno não repassa reasoning_content entre turnos,
        # então o thinking mode precisa estar desligado explicitamente.
        request_params={"thinking": {"type": "disabled"}},
    )


# --- Tools registradas no Agno ---

@tool(description="Busca informações atuais na web. Use para qualquer pergunta sobre eventos recentes, documentação, preços, notícias ou qualquer dado externo.")
def search(query: str) -> str:
    return tavily_search(query)


@tool(description="Lista todos os repositórios GitHub do Felipe (pessoal e empresa) com descrição.")
def github_list_repos() -> str:
    return list_repos()


@tool(description="Retorna os últimos commits de um repositório. Parâmetro: nome completo do repo (ex: 'usuario/repo').")
def github_recent_commits(repo_name: str, limit: int = 5) -> str:
    return get_recent_commits(repo_name, limit)


@tool(description="Lista os pull requests abertos de um repositório.")
def github_open_prs(repo_name: str) -> str:
    return list_open_prs(repo_name)


@tool(description="Lista as issues abertas de um repositório.")
def github_open_issues(repo_name: str) -> str:
    return list_open_issues(repo_name)


@tool(description="Retorna o conteúdo de um arquivo de um repositório. Parâmetros: repo_name, file_path, branch (padrão: main).")
def github_get_file(repo_name: str, file_path: str, branch: str = "main") -> str:
    return get_file(repo_name, file_path, branch)


@tool(description="Aciona o sub-agente redator para criar ou melhorar textos: emails, posts, copy, narrativas, mensagens para clientes.")
def ask_writer(task: str) -> str:
    from agents.writer import run as writer_run
    return writer_run(task)


@tool(description="Aciona o sub-agente designer para conceito visual, briefing criativo, feedback de UX/UI, paletas, estrutura de apresentações.")
def ask_designer(task: str) -> str:
    from agents.designer import run as designer_run
    return designer_run(task)


@tool(description="Aciona o sub-agente programador para código, arquitetura de sistemas, debug, revisão técnica, escolha de tecnologias.")
def ask_developer(task: str) -> str:
    from agents.developer import run as developer_run
    return developer_run(task)


# --- Agente principal ---

_agent = Agent(
    model=_make_model(),
    instructions=_SYSTEM_PROMPT,
    tools=[
        search,
        github_list_repos,
        github_recent_commits,
        github_open_prs,
        github_open_issues,
        github_get_file,
        ask_writer,
        ask_designer,
        ask_developer,
    ],
    markdown=True,
    show_tool_calls=False,
)


async def run(message: str, user_id: int) -> str:
    """Processa uma mensagem do usuário e retorna a resposta do Contra."""
    from memory.manager import save_message, get_today_messages

    logger.info("Contra processando mensagem de user_id=%s", user_id)

    save_message("user", message)

    # Injeta o histórico do dia como contexto adicional
    history = get_today_messages()
    if len(history) > 1:
        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in history[:-1]
        )
        full_message = f"<historico_do_dia>\n{history_text}\n</historico_do_dia>\n\n{message}"
    else:
        full_message = message

    try:
        response = await _agent.arun(full_message)
        content = response.content
        save_message("assistant", content)
        return content
    except Exception:
        logger.exception("Erro no orquestrador ao processar mensagem.")
        return "Erro interno. Tenta de novo."
