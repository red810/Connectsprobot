"""
Bot Factory Service for ConnectProBot
Handles creation and management of mini bots
"""

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from database import get_active_mini_bots, get_owner, check_trial_expired
from templates.footer import add_footer

logger = logging.getLogger(__name__)

# Store active mini bot applications
active_mini_bots: dict = {}


async def start_mini_bots(main_application: Application) -> None:
    """Start all active mini bots."""
    mini_bots = await get_active_mini_bots()
    
    for bot_data in mini_bots:
        try:
            await register_mini_bot(bot_data['bot_token'], bot_data['telegram_id'])
        except Exception as e:
            logger.error(f"Failed to start mini bot for owner {bot_data['telegram_id']}: {e}")


async def register_mini_bot(token: str, owner_id: int) -> bool:
    """Register and start a mini bot."""
    try:
        # Create new application for mini bot
        app = Application.builder().token(token).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", lambda u, c: mini_bot_start(u, c, owner_id)))
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            lambda u, c: mini_bot_message(u, c, owner_id)
        ))
        
        # Store reference
        active_mini_bots[owner_id] = app
        
        # Start polling in background
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        
        logger.info(f"Mini bot started for owner {owner_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to register mini bot: {e}")
        return False


async def stop_mini_bot(owner_id: int) -> bool:
    """Stop a mini bot."""
    if owner_id in active_mini_bots:
        app = active_mini_bots[owner_id]
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        del active_mini_bots[owner_id]
        logger.info(f"Mini bot stopped for owner {owner_id}")
        return True
    return False


async def mini_bot_start(update: Update, context: ContextTypes.DEFAULT_TYPE, owner_id: int) -> None:
    """Handle /start for mini bots."""
    user = update.effective_user
    owner = await get_owner(owner_id)
    
    if not owner:
        await update.message.reply_text("❌ This bot is not available.")
        return
    
    # Check trial
    if await check_trial_expired(owner_id):
        await update.message.reply_text(
            "⚠️ This bot's trial has ended.\n\n"
            "Subscription Coming Soon.\n"
            "Please wait for update."
        )
        return
    
    # Store owner context for this user
    context.user_data['owner_id'] = owner_id
    
    welcome_text = (
        f"👋 Welcome to **{owner['business_name']}**!\n\n"
        f"📝 {owner['bio'] or 'Send us a message!'}\n\n"
        "Your messages will be forwarded to the owner."
    )
    
    welcome_text = add_footer(welcome_text)
    
    await update.message.reply_text(welcome_text, parse_mode='Markdown')


async def mini_bot_message(update: Update, context: ContextTypes.DEFAULT_TYPE, owner_id: int) -> None:
    """Handle messages for mini bots."""
    user = update.effective_user
    message_text = update.message.text
    
    owner = await get_owner(owner_id)
    
    if not owner or not owner['is_active']:
        await update.message.reply_text("❌ This bot is currently unavailable.")
        return
    
    # Check trial
    if await check_trial_expired(owner_id):
        await update.message.reply_text(
            "⚠️ This bot's trial has ended.\n\n"
            "Subscription Coming Soon.\n"
            "Please wait for update."
        )
        return
    
    # Forward to owner
    try:
        # Import here to avoid circular imports
        from database import get_or_create_conversation, save_message
        
        conversation = await get_or_create_conversation(user.id, owner_id, owner['bot_token'])
        await save_message(
            conversation_id=conversation['id'],
            sender_type='user',
            message_text=message_text,
            telegram_message_id=update.message.message_id
        )
        
        forward_text = (
            f"📩 **New Message**\n\n"
            f"From: {user.first_name or 'User'} (@{user.username or 'N/A'})\n"
            f"Message: {message_text}"
        )
        
        # Send to owner via main bot or direct
        await context.bot.send_message(
            chat_id=owner_id,
            text=forward_text,
            parse_mode='Markdown'
        )
        
        response = add_footer("✅ Message sent! The owner will reply soon.")
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Failed to forward message: {e}")
        await update.message.reply_text("❌ Failed to send message. Please try again.")
