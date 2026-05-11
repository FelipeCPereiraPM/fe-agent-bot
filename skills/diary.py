import logging
from datetime import date
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import config

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)

_SYSTEM_PROMPT = """\
<instruction>
Você é um assistente que transforma o histórico de conversas do dia em um diário de bordo conciso e estruturado.
</instruction>

<rules>
- Sem introduções, cortesias ou conclusões genéricas
- Apenas o que foi discutido, decidido ou planejado tem valor
- Se não houve nada relevante, diga isso em uma linha
- Use markdown limpo
</rules>

<output-format>
# Diário de Bordo — {date}

## Decisões
- bullet com cada decisão tomada

## Tarefas
- bullet com cada tarefa mencionada (com status se conhecido)

## Ideias & Contexto
- bullet com ideias, insights ou contexto relevante para os próximos dias

## Pendências
- bullet com o que ficou em aberto
</output-format>
"""

_USER_PROMPT = """\
<conversation>
{history}
</conversation>

Gere o diário de bordo do dia com base nessa conversa.
"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
async def _call_llm(history: str) -> str:
    today = date.today().isoformat()
    response = await _client.chat.completions.create(
        model=config.DEEPSEEK_MODEL,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT.format(date=today)},
            {"role": "user", "content": _USER_PROMPT.format(history=history)},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content.strip()


async def generate_diary() -> str:
    """Gera o diário de bordo do dia e salva no banco. Retorna o texto gerado."""
    today = date.today().isoformat()

    history = _get_today_history()
    if not history:
        msg = f"Nenhuma conversa registrada hoje ({today}). Diário não gerado."
        logger.info(msg)
        return msg

    logger.info("Gerando diário para %s (%d chars de histórico).", today, len(history))

    try:
        content = await _call_llm(history)
    except Exception:
        logger.exception("Falha ao gerar diário via LLM.")
        return "Erro ao gerar o diário. Tente novamente com /diario."

    _save_diary(today, content)

    logger.info("Diário de %s gerado e salvo com sucesso.", today)
    return content


def _get_today_history() -> str:
    """Retorna o histórico da conversa do dia atual como texto."""
    from memory.manager import get_today_messages
    messages = get_today_messages()
    return "\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)


def _save_diary(date_str: str, content: str) -> None:
    """Salva o diário no PostgreSQL e limpa as mensagens do dia."""
    from memory.manager import save_diary, clear_today_messages
    save_diary(date_str, content)
    clear_today_messages()
