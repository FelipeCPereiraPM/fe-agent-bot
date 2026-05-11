import logging
from tavily import TavilyClient

import config

logger = logging.getLogger(__name__)

_client = TavilyClient(api_key=config.TAVILY_API_KEY)


def search(query: str, max_results: int = 5) -> str:
    """Busca na web via Tavily. Retorna resultados formatados como texto."""
    logger.info("Tavily search: %s", query)
    try:
        response = _client.search(
            query=query,
            max_results=max_results,
            include_answer=True,
        )
    except Exception:
        logger.exception("Erro na busca Tavily: %s", query)
        return "Erro ao realizar a busca. Tente novamente."

    parts = []

    if response.get("answer"):
        parts.append(f"**Resposta direta:** {response['answer']}\n")

    for i, result in enumerate(response.get("results", []), start=1):
        title = result.get("title", "Sem título")
        url = result.get("url", "")
        content = result.get("content", "").strip()
        parts.append(f"{i}. **{title}**\n   {url}\n   {content[:300]}{'...' if len(content) > 300 else ''}")

    if not parts:
        return "Nenhum resultado encontrado."

    return "\n\n".join(parts)


if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    result = search("Python APScheduler exemplo cron job")
    print(result)
