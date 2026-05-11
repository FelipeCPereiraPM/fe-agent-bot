import os
import logging
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise EnvironmentError(f"Variável de ambiente obrigatória não definida: {key}")
    return value.strip()


def _optional(key: str, default: str = "") -> str:
    return (os.getenv(key) or default).strip()


# Telegram
TELEGRAM_BOT_TOKEN = _require("TELEGRAM_BOT_TOKEN")
AUTHORIZED_USER_ID = int(_require("AUTHORIZED_USER_ID"))

# LLM
DEEPSEEK_API_KEY = _require("DEEPSEEK_API_KEY")
DEEPSEEK_MODEL = _optional("DEEPSEEK_MODEL", "deepseek-chat")

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

# Busca
TAVILY_API_KEY = _require("TAVILY_API_KEY")

# GitHub
GITHUB_TOKEN_PERSONAL = _optional("GITHUB_TOKEN_PERSONAL")
GITHUB_TOKEN_COMPANY = _optional("GITHUB_TOKEN_COMPANY")
GITHUB_REPOS_PERSONAL = [r.strip() for r in _optional("GITHUB_REPOS_PERSONAL").split(",") if r.strip()]
GITHUB_REPOS_COMPANY = [r.strip() for r in _optional("GITHUB_REPOS_COMPANY").split(",") if r.strip()]

# Google Calendar
GOOGLE_CLIENT_ID = _optional("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = _optional("GOOGLE_CLIENT_SECRET")
GOOGLE_REFRESH_TOKEN = _optional("GOOGLE_REFRESH_TOKEN")

# PostgreSQL
DATABASE_URL = _require("DATABASE_URL")

# Diário automático
DIARY_HOUR = int(_optional("DIARY_HOUR", "23"))
DIARY_MINUTE = int(_optional("DIARY_MINUTE", "59"))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    logger.info("Configurações carregadas com sucesso.")
    logger.info("  Telegram bot token: %s...%s", TELEGRAM_BOT_TOKEN[:6], TELEGRAM_BOT_TOKEN[-4:])
    logger.info("  Authorized user ID: %s", AUTHORIZED_USER_ID)
    logger.info("  DeepSeek model: %s", DEEPSEEK_MODEL)
    logger.info("  Repos pessoais: %s", GITHUB_REPOS_PERSONAL)
    logger.info("  Repos empresa: %s", GITHUB_REPOS_COMPANY)
    logger.info("  Diário automático: %02d:%02d", DIARY_HOUR, DIARY_MINUTE)
    logger.info("  Database URL: %s...%s", DATABASE_URL[:20], DATABASE_URL[-10:])
