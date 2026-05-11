import logging
from datetime import date
import psycopg2
from psycopg2.extras import RealDictCursor

import config

logger = logging.getLogger(__name__)

_conn = None


def _get_conn():
    global _conn
    if _conn is None or _conn.closed:
        _conn = psycopg2.connect(config.DATABASE_URL)
        _conn.autocommit = True
    return _conn


def init_db() -> None:
    """Cria as tabelas se não existirem. Chamado no startup do bot."""
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id          SERIAL PRIMARY KEY,
                date        DATE        NOT NULL DEFAULT CURRENT_DATE,
                role        VARCHAR(20) NOT NULL,
                content     TEXT        NOT NULL,
                created_at  TIMESTAMP   NOT NULL DEFAULT NOW()
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_date ON messages (date)
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS diaries (
                id          SERIAL PRIMARY KEY,
                date        DATE        NOT NULL UNIQUE,
                content     TEXT        NOT NULL,
                created_at  TIMESTAMP   NOT NULL DEFAULT NOW()
            )
        """)
    logger.info("Banco de dados inicializado.")


def validate_connection() -> None:
    """Valida a conexão com o PostgreSQL. Lança exceção se falhar."""
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        logger.info("Conexão com PostgreSQL validada.")
    except Exception as e:
        raise RuntimeError(f"Falha ao conectar ao PostgreSQL: {e}") from e


# --- Mensagens da sessão diária ---

def save_message(role: str, content: str) -> None:
    """Salva uma mensagem da conversa do dia atual."""
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO messages (role, content) VALUES (%s, %s)",
            (role, content),
        )


def get_today_messages() -> list[dict]:
    """Retorna todas as mensagens do dia atual."""
    conn = _get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT role, content, created_at FROM messages WHERE date = CURRENT_DATE ORDER BY created_at",
        )
        return [dict(row) for row in cur.fetchall()]


def clear_today_messages() -> None:
    """Apaga as mensagens do dia atual após geração do diário."""
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute("DELETE FROM messages WHERE date = CURRENT_DATE")
    logger.info("Mensagens do dia apagadas após geração do diário.")


# --- Diários ---

def save_diary(date_str: str, content: str) -> None:
    """Salva ou atualiza o diário de uma data."""
    conn = _get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO diaries (date, content)
            VALUES (%s, %s)
            ON CONFLICT (date) DO UPDATE SET content = EXCLUDED.content, created_at = NOW()
            """,
            (date_str, content),
        )
    logger.info("Diário de %s salvo.", date_str)


def get_diary(date_str: str) -> dict | None:
    """Retorna o diário de uma data específica ou None se não existir."""
    conn = _get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT date::text, content, created_at FROM diaries WHERE date = %s",
            (date_str,),
        )
        row = cur.fetchone()
        return dict(row) if row else None


def list_diaries(limit: int = 10) -> list[dict]:
    """Lista os diários mais recentes com preview das primeiras 80 chars."""
    conn = _get_conn()
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT date::text, LEFT(content, 80) AS preview
            FROM diaries
            ORDER BY date DESC
            LIMIT %s
            """,
            (limit,),
        )
        return [dict(row) for row in cur.fetchall()]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    validate_connection()
    init_db()

    save_message("user", "Mensagem de teste")
    save_message("assistant", "Resposta de teste")
    msgs = get_today_messages()
    logger.info("Mensagens hoje: %d", len(msgs))
    for m in msgs:
        logger.info("  [%s] %s", m["role"], m["content"])

    save_diary(date.today().isoformat(), "# Diário de teste\n\n## Decisões\n- Testou o banco")
    entry = get_diary(date.today().isoformat())
    logger.info("Diário salvo: %s", entry["date"])

    entries = list_diaries()
    logger.info("Total de diários: %d", len(entries))
