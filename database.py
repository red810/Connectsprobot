import asyncpg
from typing import Optional
import logging
from config import DATABASE_URL, MESSAGE_RETENTION_DAYS

logger = logging.getLogger(__name__)

pool: Optional[asyncpg.Pool] = None


async def init_db() -> None:
    """Initialize database connection pool and create tables."""
    global pool

    # Append SSL mode if missing
    if "sslmode" not in DATABASE_URL:
        db_url = DATABASE_URL + "?sslmode=require"
    else:
        db_url = DATABASE_URL

    pool = await asyncpg.create_pool(
        db_url,
        min_size=1,
        max_size=5
    )

    async with pool.acquire() as conn:
        # Users Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                first_name VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Owners Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS owners (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                business_name VARCHAR(255),
                category VARCHAR(100),
                bio TEXT,
                logo_file_id VARCHAR(255),
                bot_type VARCHAR(50) DEFAULT 'this_bot',
                bot_token VARCHAR(255),
                mini_bot_username VARCHAR(255),
                trial_start TIMESTAMP,
                trial_expired BOOLEAN DEFAULT FALSE,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                onboarding_step VARCHAR(50) DEFAULT 'name'
            );
        """)

        # Conversations Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                owner_id BIGINT NOT NULL,
                bot_token VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_message TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count_today INT DEFAULT 0,
                last_message_date DATE DEFAULT CURRENT_DATE,
                UNIQUE(user_id, owner_id)
            );
        """)

        # Messages Table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                conversation_id INT REFERENCES conversations(id) ON DELETE CASCADE,
                sender_type VARCHAR(10) NOT NULL,
                message_text TEXT,
                message_type VARCHAR(20) DEFAULT 'text',
                telegram_message_id BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    logger.info("🚀 Database Connected & Tables Ready (Railway Mode)")


async def cleanup_old_messages() -> None:
    """Auto delete old messages based on retention days."""
    if not pool:
        return

    async with pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM messages
            WHERE created_at < NOW() - ($1 || ' days')::INTERVAL
        """, MESSAGE_RETENTION_DAYS)

    logger.info("🧹 Old messages deleted")
    # ---------------- USER FUNCTIONS ---------------- #

async def create_user(telegram_id, username, first_name):
    if not pool:
        return

    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (telegram_id, username, first_name)
            VALUES ($1, $2, $3)
            ON CONFLICT (telegram_id) DO UPDATE
            SET username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_active = CURRENT_TIMESTAMP;
        """, telegram_id, username, first_name)


async def get_user(telegram_id):
    if not pool:
        return None

    async with pool.acquire() as conn:
        return await conn.fetchrow("""
            SELECT * FROM users WHERE telegram_id = $1
        """, telegram_id)


# ---------------- OWNER FUNCTIONS ---------------- #

async def create_owner(telegram_id, username):
    if not pool:
        return

    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO owners (telegram_id, username)
            VALUES ($1, $2)
            ON CONFLICT (telegram_id) DO NOTHING;
        """, telegram_id, username)


async def get_owner(telegram_id):
    if not pool:
        return None

    async with pool.acquire() as conn:
        return await conn.fetchrow("""
            SELECT * FROM owners WHERE telegram_id = $1
        """, telegram_id)
