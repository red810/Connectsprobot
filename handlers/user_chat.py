"""
User chat handler for ConnectProBot
Handles messages between users and owners
"""

from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes

from config import FREE_MODE_MESSAGE_LIMIT, FREE_MODE_START_HOUR, FREE_MODE_END_HOUR, FREE_MODE_END_MINUTE
from database import (
    get_owner, get_or_create_conversation, save_message,
    check_message_limit, increment_message_count, check_trial_expired
)
from templates.footer import add_footer


async def user_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming user messages."""
    user = update.effective_user
    message_text = update.message.text
    
    # Check if user is in onboarding flow
    onboarding_step = context.user_data.get('onboarding_step')
    if onboarding_step and onboarding_step != 'done':
        # Route to appropriate onboarding handler
        from handlers.owner_onboarding import business_name_handler, bio_handler, bot_token_handler
        
        if onboarding_step == 'name':
            await business_name_handler(update, context)
        elif onboarding_step == 'bio':
            await bio_handler(update, context)
        elif onboarding_step == 'token':
            await bot_token_handler(update, context)
        return
    
    # Check if user is contacting an owner
    owner_id = context.user_data.get('contacting_owner')
    if not owner_id:
        await update.message.reply_text(
            "👋 Welcome! Use /start to begin or use a channel's direct link."
        )
        return
    
    owner = await get_owner(owner_id)
    if not owner:
        await update.message.reply_text("❌ This business is no longer available.")
        context.user_data.pop('contacting_owner', None)
        return
    
    # Check if owner is active
    if not owner['is_active']:
        await update.message.reply_text("❌ This business is currently inactive.")
        return
    
    # Check trial expiry for mini bots
    if owner['bot_type'] == 'own_bot':
        if await check_trial_expired(owner_id):
            await update.message.reply_text(
                "⚠️ This bot's trial has ended.\n\n"
                "Subscription Coming Soon.\n"
                "Please wait for update."
            )
            return
    else:
        # Free mode restrictions
        # Check time restrictions
        now = datetime.utcnow()
        current_hour = now.hour
        current_minute = now.minute
        
        if current_hour < FREE_MODE_START_HOUR or (current_hour >= FREE_MODE_END_HOUR and current_minute >= FREE_MODE_END_MINUTE):
            await update.message.reply_text(
                f"⏰ Free mode is active only from {FREE_MODE_START_HOUR}:00 AM to {FREE_MODE_END_HOUR}:{FREE_MODE_END_MINUTE:02d} PM.\n\n"
                "Please try again during active hours!"
            )
            return
        
        # Check message limit
        can_send = await check_message_limit(user.id, owner_id, FREE_MODE_MESSAGE_LIMIT)
        if not can_send:
            await update.message.reply_text(
                f"📫 You've reached your daily limit of {FREE_MODE_MESSAGE_LIMIT} messages.\n\n"
                "Try again tomorrow!"
            )
            return
    
    # Get or create conversation
    conversation = await get_or_create_conversation(user.id, owner_id, owner.get('bot_token'))
    
    # Save message
    await save_message(
        conversation_id=conversation['id'],
        sender_type='user',
        message_text=message_text,
        telegram_message_id=update.message.message_id
    )
    
    # Increment message count for free mode
    if owner['bot_type'] == 'this_bot':
        await increment_message_count(user.id, owner_id)
    
    # Forward message to owner
    try:
        forward_text = (
            f"📩 **New Message**\n\n"
            f"From: {user.first_name or 'User'}\n"
            f"Message: {message_text}\n\n"
            f"_Reply to this message to respond_"
        )
        
        await context.bot.send_message(
            chat_id=owner_id,
            text=forward_text,
            parse_mode='Markdown'
        )
        
        await update.message.reply_text("✅ Message sent! The owner will reply soon.")
        
    except Exception as e:
        await update.message.reply_text("❌ Failed to deliver message. Please try again.")


async def owner_reply_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle owner replies to users."""
    owner = update.effective_user
    
    # Check if this is a reply to a forwarded message
    if not update.message.reply_to_message:
        return
    
    owner_data = await get_owner(owner.id)
    if not owner_data:
        return
    
    # Extract user info from the replied message
    # This is a simplified version - in production you'd want to store
    # message mappings in the database
    
    reply_text = update.message.text
    
    # Add footer for mini bots
    if owner_data['bot_type'] == 'own_bot':
        reply_text = add_footer(reply_text)
    
    # The actual reply logic would need message mapping
    # For now, we'll just confirm the reply was sent
    await update.message.reply_text("✅ Reply sent!")
