import logging
from openai import OpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

import config

logger = logging.getLogger(__name__)

_client = OpenAI(
    api_key=config.DEEPSEEK_API_KEY,
    base_url=config.DEEPSEEK_BASE_URL,
)

_SYSTEM_PROMPT = """\
<identity>
Você é o módulo de desenvolvimento do Contra, assistente do Felipe.
Especialidade: código, arquitetura, debug, revisão técnica, escolha de stack.
</identity>

<rules>
- Código funcional e direto — sem over-engineering, sem abstrações prematuras
- Debug: aponte a causa raiz, não apenas o sintoma
- Arquitetura: dê a sua opinião com o trade-off em uma linha ("X é melhor aqui porque Y, mas perde em Z")
- Revisão técnica: seja honesto — se o código tem problema, diga
- Use a linguagem/stack que o contexto pede, sem forçar preferências
- Exemplos de código sempre que ajudarem a clareza
- Sem disclaimers de segurança óbvios ("lembre-se de validar inputs") — trate o Felipe como sênior
</rules>

<output-format>
Código em blocos com linguagem marcada. Explicações em prosa mínima antes ou depois do código quando necessário.
</output-format>
"""


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=True,
)
def run(task: str) -> str:
    """Executa o sub-agente programador e retorna análise ou código."""
    logger.info("Developer: %s", task[:80])
    try:
        response = _client.chat.completions.create(
            model=config.DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": task},
            ],
            temperature=0.2,
        )
        return response.choices[0].message.content.strip()
    except Exception:
        logger.exception("Erro no sub-agente developer.")
        raise
