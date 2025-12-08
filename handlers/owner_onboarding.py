"""
Owner onboarding handlers for ConnectProBot
"""

import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import CATEGORIES, BOT_USERNAME
from database import update_owner, get_owner
from services.bot_factory import register_mini_bot


async def business_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle business name input."""
    if context.user_data.get('onboarding_step') != 'name':
        return
    
    business_name = update.message.text.strip()
    
    if len(business_name) < 2 or len(business_name) > 100:
        await update.message.reply_text("❌ Name must be 2-100 characters. Try again:")
        return
    
    await update_owner(update.effective_user.id, business_name=business_name)
    context.user_data['onboarding_step'] = 'category'
    
    # Create category buttons
    keyboard = [[InlineKeyboardButton(cat, callback_data=f"cat_{cat}")] for cat in CATEGORIES]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"✅ Name saved: **{business_name}**\n\n"
        "📂 **Step 2:** Select your category:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def category_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle category selection callback."""
    query = update.callback_query
    await query.answer()
    
    if not query.data.startswith('cat_'):
        return
    
    category = query.data.replace('cat_', '')
    await update_owner(update.effective_user.id, category=category)
    context.user_data['onboarding_step'] = 'bio'
    
    await query.edit_message_text(
        f"✅ Category: **{category}**\n\n"
        "📝 **Step 3:** Write a short bio for your business (max 500 chars):",
        parse_mode='Markdown'
    )


async def bio_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle bio input."""
    if context.user_data.get('onboarding_step') != 'bio':
        return
    
    bio = update.message.text.strip()
    
    if len(bio) > 500:
        await update.message.reply_text("❌ Bio too long! Keep it under 500 characters:")
        return
    
    await update_owner(update.effective_user.id, bio=bio)
    context.user_data['onboarding_step'] = 'logo'
    
    keyboard = [[InlineKeyboardButton("⏭ Skip Logo", callback_data="skip_logo")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "✅ Bio saved!\n\n"
        "🖼 **Step 4:** Upload your logo (optional):",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def logo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle logo upload."""
    if context.user_data.get('onboarding_step') != 'logo':
        return
    
    if update.message.photo:
        photo = update.message.photo[-1]  # Get highest resolution
        await update_owner(update.effective_user.id, logo_file_id=photo.file_id)
        await update.message.reply_text("✅ Logo saved!")
    
    await finish_onboarding_or_ask_token(update, context)


async def skip_logo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle skip logo callback."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "skip_logo":
        context.user_data['onboarding_step'] = 'token' if context.user_data.get('bot_type') == 'own_bot' else 'done'
        await finish_onboarding_or_ask_token(update, context)


async def finish_onboarding_or_ask_token(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Finish onboarding or ask for bot token."""
    user_id = update.effective_user.id
    bot_type = context.user_data.get('bot_type', 'this_bot')
    
    if bot_type == 'own_bot':
        context.user_data['onboarding_step'] = 'token'
        
        message = update.callback_query.message if update.callback_query else update.message
        await message.reply_text(
            "🤖 **Step 5:** Enter your Bot Token\n\n"
            "**How to get a token:**\n"
            "1️⃣ Open @BotFather\n"
            "2️⃣ Send /newbot\n"
            "3️⃣ Follow instructions\n"
            "4️⃣ Copy the token and paste here\n\n"
            "⚠️ Keep your token private!",
            parse_mode='Markdown'
        )
    else:
        await complete_onboarding(update, context)


async def bot_token_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle bot token input."""
    if context.user_data.get('onboarding_step') != 'token':
        return
    
    token = update.message.text.strip()
    
    # Validate token with getMe()
    is_valid, bot_info = await validate_bot_token(token)
    
    if not is_valid:
        await update.message.reply_text(
            "❌ Invalid token! Please check and try again.\n\n"
            "Make sure you copied the full token from @BotFather."
        )
        return
    
    # Save token and bot username
    await update_owner(
        update.effective_user.id,
        bot_token=token,
        mini_bot_username=f"@{bot_info['username']}"
    )
    
    # Register the mini bot
    await register_mini_bot(token, update.effective_user.id)
    
    await update.message.reply_text(
        f"✅ Bot validated: @{bot_info['username']}\n\n"
        "Your mini bot is now active!"
    )
    
    await complete_onboarding(update, context)


async def validate_bot_token(token: str) -> tuple[bool, dict]:
    """Validate bot token using Telegram API."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://api.telegram.org/bot{token}/getMe") as resp:
                data = await resp.json()
                if data.get('ok'):
                    return True, data['result']
                return False, {}
    except Exception:
        return False, {}


async def complete_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Complete the onboarding process."""
    user_id = update.effective_user.id
    owner = await get_owner(user_id)
    bot_type = context.user_data.get('bot_type', 'this_bot')
    
    context.user_data['onboarding_step'] = 'done'
    await update_owner(user_id, onboarding_step='done')
    
    message = update.callback_query.message if update.callback_query else update.message
    
    if bot_type == 'own_bot':
        share_link = f"https://t.me/{owner['mini_bot_username'].replace('@', '')}?start=owner_{user_id}"
        text = (
            "🎉 **Setup Complete!**\n\n"
            f"🏢 **Business:** {owner['business_name']}\n"
            f"📂 **Category:** {owner['category']}\n"
            f"🤖 **Your Bot:** {owner['mini_bot_username']}\n\n"
            f"📤 **Share this link:**\n`{share_link}`\n\n"
            "Your 4-month free trial has started!\n\n"
            "Use /dashboard to manage your bot."
        )
    else:
        share_link = f"https://t.me/{BOT_USERNAME.replace('@', '')}?start=owner_{user_id}"
        text = (
            "🎉 **Setup Complete!**\n\n"
            f"🏢 **Business:** {owner['business_name']}\n"
            f"📂 **Category:** {owner['category']}\n\n"
            f"📤 **Share this link:**\n`{share_link}`\n\n"
            "Users can now contact you through this bot!\n\n"
            "💡 **Tip:** Upgrade to your own bot for unlimited features!"
        )
    
    await message.reply_text(text, parse_mode='Markdown')
