"""
ConnectProBot - Main Entry Point
Production-grade Telegram SaaS bot system
"""

import asyncio
import logging
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, ADMIN_IDS
from database import init_db, cleanup_old_messages
from handlers.start import start_handler
from handlers.registration import register_callback_handler
from handlers.owner_onboarding import (
    business_name_handler, category_handler, bio_handler, 
    logo_handler, bot_token_handler
)
from handlers.user_chat import user_message_handler
from handlers.admin_panel import admin_handler, admin_callback_handler
from services.bot_factory import start_mini_bots

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application: Application) -> None:
    """Initialize database and start mini bots after main bot starts."""
    await init_db()
    logger.info("Database initialized")
    
    # Start all active mini bots
    await start_mini_bots(application)
    logger.info("Mini bots started")


def setup_scheduler() -> AsyncIOScheduler:
    """Setup APScheduler for scheduled tasks."""
    scheduler = AsyncIOScheduler()
    
    # Run message cleanup daily at 3 AM
    scheduler.add_job(
        cleanup_old_messages,
        'cron',
        hour=3,
        minute=0,
        id='cleanup_messages',
        replace_existing=True
    )
    
    return scheduler


def main() -> None:
    """Start the bot."""
    # Create application
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("admin", admin_handler))
    application.add_handler(CommandHandler("dashboard", lambda u, c: None))  # Placeholder
    
    # Callback query handlers
    application.add_handler(CallbackQueryHandler(register_callback_handler, pattern="^register$"))
    application.add_handler(CallbackQueryHandler(register_callback_handler, pattern="^start_this_bot$"))
    application.add_handler(CallbackQueryHandler(register_callback_handler, pattern="^start_own_bot$"))
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^admin_"))
    
    # Message handlers for onboarding flow
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND, 
        user_message_handler
    ))
    application.add_handler(MessageHandler(filters.PHOTO, logo_handler))

    # Setup and start scheduler
    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("Scheduler started")

    # Run the bot
    logger.info("Starting ConnectProBot...")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
