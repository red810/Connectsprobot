"""
Start command handler for ConnectProBot
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from templates.intro_text import INTRO_MESSAGE
from database import create_user, get_owner


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    user = update.effective_user
    
    # Create or update user in database
    await create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    
    # Check if user came from a referral link (deep link)
    args = context.args
    if args and args[0].startswith('owner_'):
        # User is contacting an owner
        owner_id = int(args[0].replace('owner_', ''))
        owner = await get_owner(owner_id)
        
        if owner and owner['is_active']:
            context.user_data['contacting_owner'] = owner_id
            await update.message.reply_text(
                f"👋 Welcome! You're connected to **{owner['business_name']}**.\n\n"
                f"📝 {owner['bio'] or 'No bio set'}\n\n"
                "Send your message below and the owner will reply soon!",
                parse_mode='Markdown'
            )
            return
    
    # Show intro message with Register button
    keyboard = [
        [InlineKeyboardButton("📝 Register", callback_data="register")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        INTRO_MESSAGE,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
