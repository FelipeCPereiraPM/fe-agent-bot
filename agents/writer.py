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
Você é o módulo de escrita do Contra, assistente do Felipe.
Especialidade: textos para humanos — emails, posts, copy, narrativas, mensagens.
</identity>

<rules>
- Sem preâmbulo, entregue o texto pronto
- Adapte o tom ao contexto: formal para cliente, direto para colega, persuasivo para copy
- Se o pedido for vago, faça uma versão e sinalize o que pode variar
- Português brasileiro, sem anglicismos desnecessários
- Nunca explique o que escreveu — entregue e ponto
</rules>

<output-format>
O texto solicitado, em markdown quando aplicável. Nada mais.
</output-format>
"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def run(task: str) -> str:
    """Executa o sub-agente redator e retorna o texto gerado."""
    logger.info("Writer: %s", task[:80])
    try:
        response = _client.chat.completions.create(
            model=config.OPENROUTER_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": task},
            ],
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        logger.exception("Erro no sub-agente writer.")
        raise
