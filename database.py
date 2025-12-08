"""
Database operations for ConnectProBot
Uses asyncpg for async PostgreSQL operations
"""

import asyncpg
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

from config import DATABASE_URL, MESSAGE_RETENTION_DAYS

logger = logging.getLogger(__name__)

# Connection pool
pool: Optional[asyncpg.Pool] = None


async def init_db() -> None:
    """Initialize database connection pool and create tables."""
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    
    async with pool.acquire() as conn:
        # Create users table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                telegram_id BIGINT UNIQUE NOT NULL,
                username VARCHAR(255),
                first_name VARCHAR(255),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create owners table
        await conn.execute('''
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
            )
        ''')
        
        # Create conversations table
        await conn.execute('''
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
            )
        ''')
        
        # Create messages table
        await conn.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                conversation_id INT REFERENCES conversations(id) ON DELETE CASCADE,
                sender_type VARCHAR(10) NOT NULL,
                message_text TEXT,
                message_type VARCHAR(20) DEFAULT 'text',
                telegram_message_id BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_owners_telegram_id ON owners(telegram_id)')
        await conn.execute('CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)')
        
    logger.info("Database tables created successfully")


async def get_user(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Get user by telegram ID."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT * FROM users WHERE telegram_id = $1', telegram_id
        )
        return dict(row) if row else None


async def create_user(telegram_id: int, username: str = None, first_name: str = None) -> Dict[str, Any]:
    """Create a new user."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO users (telegram_id, username, first_name)
            VALUES ($1, $2, $3)
            ON CONFLICT (telegram_id) DO UPDATE SET
                username = EXCLUDED.username,
                first_name = EXCLUDED.first_name,
                last_active = CURRENT_TIMESTAMP
            RETURNING *
        ''', telegram_id, username, first_name)
        return dict(row)


async def get_owner(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Get owner by telegram ID."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            'SELECT * FROM owners WHERE telegram_id = $1', telegram_id
        )
        return dict(row) if row else None


async def create_owner(telegram_id: int, username: str = None, bot_type: str = 'this_bot') -> Dict[str, Any]:
    """Create a new owner."""
    async with pool.acquire() as conn:
        trial_start = datetime.utcnow() if bot_type == 'own_bot' else None
        row = await conn.fetchrow('''
            INSERT INTO owners (telegram_id, username, bot_type, trial_start)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (telegram_id) DO UPDATE SET
                bot_type = EXCLUDED.bot_type,
                trial_start = COALESCE(owners.trial_start, EXCLUDED.trial_start)
            RETURNING *
        ''', telegram_id, username, bot_type, trial_start)
        return dict(row)


async def update_owner(telegram_id: int, **kwargs) -> Optional[Dict[str, Any]]:
    """Update owner fields."""
    if not kwargs:
        return await get_owner(telegram_id)
    
    set_clauses = ', '.join([f"{k} = ${i+2}" for i, k in enumerate(kwargs.keys())])
    values = [telegram_id] + list(kwargs.values())
    
    async with pool.acquire() as conn:
        row = await conn.fetchrow(f'''
            UPDATE owners SET {set_clauses}
            WHERE telegram_id = $1
            RETURNING *
        ''', *values)
        return dict(row) if row else None


async def get_all_owners() -> List[Dict[str, Any]]:
    """Get all owners."""
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT * FROM owners ORDER BY created_at DESC')
        return [dict(row) for row in rows]


async def get_active_mini_bots() -> List[Dict[str, Any]]:
    """Get all active mini bots with valid tokens."""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT * FROM owners 
            WHERE bot_type = 'own_bot' 
            AND bot_token IS NOT NULL 
            AND is_active = TRUE
            AND trial_expired = FALSE
        ''')
        return [dict(row) for row in rows]


async def get_or_create_conversation(user_id: int, owner_id: int, bot_token: str = None) -> Dict[str, Any]:
    """Get or create a conversation between user and owner."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO conversations (user_id, owner_id, bot_token)
            VALUES ($1, $2, $3)
            ON CONFLICT (user_id, owner_id) DO UPDATE SET
                last_message = CURRENT_TIMESTAMP
            RETURNING *
        ''', user_id, owner_id, bot_token)
        return dict(row)


async def save_message(conversation_id: int, sender_type: str, message_text: str, 
                       message_type: str = 'text', telegram_message_id: int = None) -> Dict[str, Any]:
    """Save a message to the database."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            INSERT INTO messages (conversation_id, sender_type, message_text, message_type, telegram_message_id)
            VALUES ($1, $2, $3, $4, $5)
            RETURNING *
        ''', conversation_id, sender_type, message_text, message_type, telegram_message_id)
        return dict(row)


async def check_message_limit(user_id: int, owner_id: int, limit: int) -> bool:
    """Check if user has reached daily message limit."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT message_count_today, last_message_date
            FROM conversations
            WHERE user_id = $1 AND owner_id = $2
        ''', user_id, owner_id)
        
        if not row:
            return True
        
        today = datetime.utcnow().date()
        if row['last_message_date'] != today:
            # Reset counter for new day
            await conn.execute('''
                UPDATE conversations 
                SET message_count_today = 0, last_message_date = $3
                WHERE user_id = $1 AND owner_id = $2
            ''', user_id, owner_id, today)
            return True
        
        return row['message_count_today'] < limit


async def increment_message_count(user_id: int, owner_id: int) -> None:
    """Increment daily message count for conversation."""
    async with pool.acquire() as conn:
        await conn.execute('''
            UPDATE conversations 
            SET message_count_today = message_count_today + 1,
                last_message = CURRENT_TIMESTAMP
            WHERE user_id = $1 AND owner_id = $2
        ''', user_id, owner_id)


async def get_owner_stats(owner_id: int) -> Dict[str, int]:
    """Get statistics for an owner."""
    async with pool.acquire() as conn:
        total_users = await conn.fetchval('''
            SELECT COUNT(DISTINCT user_id) FROM conversations WHERE owner_id = $1
        ''', owner_id)
        
        total_messages = await conn.fetchval('''
            SELECT COUNT(*) FROM messages m
            JOIN conversations c ON m.conversation_id = c.id
            WHERE c.owner_id = $1
        ''', owner_id)
        
        return {
            'total_users': total_users or 0,
            'total_messages': total_messages or 0
        }


async def cleanup_old_messages() -> int:
    """Delete messages older than MESSAGE_RETENTION_DAYS. Returns count of deleted messages."""
    cutoff_date = datetime.utcnow() - timedelta(days=MESSAGE_RETENTION_DAYS)
    
    async with pool.acquire() as conn:
        result = await conn.execute('''
            DELETE FROM messages WHERE created_at < $1
        ''', cutoff_date)
        
        # Parse the result to get count
        count = int(result.split()[-1]) if result else 0
        logger.info(f"Cleaned up {count} old messages")
        return count


async def check_trial_expired(owner_id: int) -> bool:
    """Check if owner's trial has expired."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow('''
            SELECT trial_start, trial_expired FROM owners WHERE telegram_id = $1
        ''', owner_id)
        
        if not row or not row['trial_start']:
            return False
        
        if row['trial_expired']:
            return True
        
        # Check if 4 months have passed
        trial_end = row['trial_start'] + timedelta(days=120)
        if datetime.utcnow() > trial_end:
            await conn.execute('''
                UPDATE owners SET trial_expired = TRUE WHERE telegram_id = $1
            ''', owner_id)
            return True
        
        return False


async def get_all_users_for_broadcast() -> List[int]:
    """Get all user telegram IDs for broadcast."""
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT telegram_id FROM users')
        return [row['telegram_id'] for row in rows]


async def get_mini_bot_users_for_broadcast() -> List[int]:
    """Get telegram IDs of users who have used mini bots."""
    async with pool.acquire() as conn:
        rows = await conn.fetch('''
            SELECT DISTINCT c.user_id FROM conversations c
            JOIN owners o ON c.owner_id = o.telegram_id
            WHERE o.bot_type = 'own_bot'
        ''')
        return [row['user_id'] for row in rows]


async def get_owner_ids_for_broadcast() -> List[int]:
    """Get all owner telegram IDs for broadcast."""
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT telegram_id FROM owners')
        return [row['telegram_id'] for row in rows]
