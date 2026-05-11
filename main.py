import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

import config
from memory.manager import validate_connection, init_db
from scheduler import start_scheduler, start_scheduler_async

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def authorized_only(handler):
    """Decorator que rejeita silenciosamente mensagens de usuários não autorizados."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id if update.effective_user else None
        if user_id != config.AUTHORIZED_USER_ID:
            logger.warning("Acesso negado para user_id=%s", user_id)
            return
        return await handler(update, context)
    return wrapper


@authorized_only
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from orchestrator import run
    text = update.message.text or ""
    logger.info("Mensagem recebida: %s", text[:80])

    await update.message.chat.send_action("typing")

    response = await run(text, user_id=config.AUTHORIZED_USER_ID)

    # Telegram tem limite de 4096 chars por mensagem
    for chunk in _split_message(response):
        await update.message.reply_text(chunk)


@authorized_only
async def cmd_diario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from skills.diary import generate_diary
    await update.message.reply_text("Gerando diário de bordo...")
    result = await generate_diary()
    await update.message.reply_text(result)


@authorized_only
async def cmd_diarios(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from memory.manager import list_diaries
    entries = list_diaries()
    if not entries:
        await update.message.reply_text("Nenhum diário encontrado.")
        return
    lines = [f"• {e['date']} — {e['preview']}" for e in entries]
    await update.message.reply_text("\n".join(lines))


@authorized_only
async def cmd_diario_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from memory.manager import get_diary
    if not context.args:
        await update.message.reply_text("Uso: /diario <data>  ex: /diario 2026-05-11")
        return
    date_str = context.args[0]
    entry = get_diary(date_str)
    if not entry:
        await update.message.reply_text(f"Nenhum diário encontrado para {date_str}.")
        return
    for chunk in _split_message(entry["content"]):
        await update.message.reply_text(chunk)


def _split_message(text: str, limit: int = 4096) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:limit])
        text = text[limit:]
    return chunks


def main():
    validate_connection()
    init_db()

    start_scheduler()

    app = (
        ApplicationBuilder()
        .token(config.TELEGRAM_BOT_TOKEN)
        .post_init(start_scheduler_async)
        .build()
    )

    app.add_handler(CommandHandler("diario", cmd_diario_date))
    app.add_handler(CommandHandler("diarios", cmd_diarios))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Fe-Agent iniciado. Aguardando mensagens...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
