"""
Registration callback handlers for ConnectProBot
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database import create_owner, get_owner


async def register_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle registration callbacks."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    callback_data = query.data
    
    if callback_data == "register":
        # Show bot type selection
        keyboard = [
            [InlineKeyboardButton(
                "🤖 Start With This Bot (Free)", 
                callback_data="start_this_bot"
            )],
            [InlineKeyboardButton(
                "🚀 Start Your Own Bot (4 months free)", 
                callback_data="start_own_bot"
            )]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "**Choose your option:**\n\n"
            "🤖 **Start With This Bot** — Use ConnectProBot directly (Free with limits)\n\n"
            "🚀 **Start Your Own Bot** — Create your own branded bot (4 months free trial)",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif callback_data == "start_this_bot":
        # Create owner with this_bot type
        await create_owner(
            telegram_id=user.id,
            username=user.username,
            bot_type='this_bot'
        )
        
        context.user_data['onboarding_step'] = 'name'
        context.user_data['bot_type'] = 'this_bot'
        
        await query.edit_message_text(
            "✅ Great choice!\n\n"
            "**Free Mode Features:**\n"
            "• Receive & reply to users\n"
            "• Basic message filter\n"
            "• 2 messages per user per day\n"
            "• Active 9:00 AM – 11:50 PM\n\n"
            "📝 **Step 1/4:** What's your Business/Channel name?",
            parse_mode='Markdown'
        )
    
    elif callback_data == "start_own_bot":
        # Create owner with own_bot type
        await create_owner(
            telegram_id=user.id,
            username=user.username,
            bot_type='own_bot'
        )
        
        context.user_data['onboarding_step'] = 'name'
        context.user_data['bot_type'] = 'own_bot'
        
        await query.edit_message_text(
            "🚀 **Excellent choice!**\n\n"
            "You'll get **4 months completely FREE!**\n\n"
            "After that, you'll need a subscription (coming soon).\n\n"
            "📝 **Step 1/5:** What's your Business/Channel name?",
            parse_mode='Markdown'
        )
