import logging
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import config

logger = logging.getLogger(__name__)

_client = OpenAI(
    api_key=config.OPENROUTER_API_KEY,
    base_url=config.OPENROUTER_BASE_URL,
)

_SYSTEM_PROMPT = """\
<identity>
Você é o módulo de design do Contra, assistente do Felipe.
Especialidade: conceito visual, briefing criativo, feedback de UX/UI, estrutura de apresentações.
</identity>

<rules>
- Pense em termos de hierarquia visual, fluxo do usuário e clareza da comunicação
- Feedback de design: seja específico — "o CTA está perdido porque não há contraste suficiente" em vez de "melhorar o botão"
- Briefings: estruture em problema, público, tom, referências, restrições
- Não invente tendências — baseie sugestões em princípios sólidos de design
- Sem elogios ao pedido, vá direto à análise ou entrega
</rules>

<output-format>
Estruturado em tópicos quando for análise ou briefing. Direto quando for resposta pontual.
</output-format>
"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def run(task: str) -> str:
    """Executa o sub-agente designer e retorna a análise ou briefing."""
    logger.info("Designer: %s", task[:80])
    try:
        response = _client.chat.completions.create(
            model=config.OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": task},
            ],
            temperature=0.5,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        logger.exception("Erro no sub-agente designer.")
        raise
