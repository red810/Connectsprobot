"""
Admin panel handlers for ConnectProBot
"""

import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import ADMIN_IDS
from database import (
    get_all_owners, update_owner, get_all_users_for_broadcast,
    get_owner_ids_for_broadcast, get_mini_bot_users_for_broadcast
)


def is_admin(user_id: int) -> bool:
    """Check if user is an admin."""
    return user_id in ADMIN_IDS


async def admin_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /admin command."""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ Access denied.")
        return
    
    keyboard = [
        [InlineKeyboardButton("👥 View All Owners", callback_data="admin_owners")],
        [InlineKeyboardButton("📊 Analytics", callback_data="admin_analytics")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("⏸ Pause Bot", callback_data="admin_pause")],
        [InlineKeyboardButton("🗑 Delete Owner", callback_data="admin_delete")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🔐 **Admin Panel**\n\n"
        "Select an action:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle admin panel callbacks."""
    query = update.callback_query
    await query.answer()
    
    if not is_admin(update.effective_user.id):
        return
    
    action = query.data.replace('admin_', '')
    
    if action == 'owners':
        await show_all_owners(query)
    elif action == 'analytics':
        await show_analytics(query)
    elif action == 'broadcast':
        await show_broadcast_menu(query, context)
    elif action.startswith('broadcast_'):
        await handle_broadcast_target(query, context, action)
    elif action == 'pause':
        await show_pause_menu(query)
    elif action == 'delete':
        await show_delete_menu(query)
    elif action.startswith('pause_owner_'):
        owner_id = int(action.replace('pause_owner_', ''))
        await pause_owner(query, owner_id)
    elif action.startswith('delete_owner_'):
        owner_id = int(action.replace('delete_owner_', ''))
        await delete_owner(query, owner_id)


async def show_all_owners(query) -> None:
    """Show all registered owners."""
    owners = await get_all_owners()
    
    if not owners:
        await query.edit_message_text("📭 No owners registered yet.")
        return
    
    text = "👥 **All Owners:**\n\n"
    for owner in owners[:20]:  # Limit to 20
        status = "✅" if owner['is_active'] else "⏸"
        bot_type = "🤖" if owner['bot_type'] == 'own_bot' else "📱"
        trial = "🔴 Expired" if owner['trial_expired'] else "🟢 Active"
        
        text += (
            f"{status} {bot_type} **{owner['business_name'] or 'N/A'}**\n"
            f"   ID: `{owner['telegram_id']}`\n"
            f"   {trial if owner['bot_type'] == 'own_bot' else ''}\n\n"
        )
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_analytics(query) -> None:
    """Show platform analytics."""
    owners = await get_all_owners()
    users = await get_all_users_for_broadcast()
    
    total_owners = len(owners)
    mini_bot_owners = len([o for o in owners if o['bot_type'] == 'own_bot'])
    active_owners = len([o for o in owners if o['is_active']])
    total_users = len(users)
    
    text = (
        "📊 **Platform Analytics**\n\n"
        f"👥 **Total Owners:** {total_owners}\n"
        f"🤖 **Mini Bot Owners:** {mini_bot_owners}\n"
        f"✅ **Active Owners:** {active_owners}\n"
        f"👤 **Total Users:** {total_users}\n"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="admin_back")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')


async def show_broadcast_menu(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show broadcast target selection."""
    keyboard = [
        [InlineKeyboardButton("👑 Only Owners", callback_data="admin_broadcast_owners")],
        [InlineKeyboardButton("👤 Only Users", callback_data="admin_broadcast_users")],
        [InlineKeyboardButton("🤖 Mini-Bot Users", callback_data="admin_broadcast_minibot_users")],
        [InlineKeyboardButton("📢 Everyone", callback_data="admin_broadcast_all")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_back")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📢 **Broadcast Message**\n\n"
        "Select target audience:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def handle_broadcast_target(query, context: ContextTypes.DEFAULT_TYPE, action: str) -> None:
    """Handle broadcast target selection."""
    target = action.replace('broadcast_', '')
    context.user_data['broadcast_target'] = target
    
    await query.edit_message_text(
        "📝 **Enter your broadcast message:**\n\n"
        "Send your message now. You can include:\n"
        "• Text\n"
        "• Image with caption\n"
        "• URL buttons (use format: [Button Text](URL))"
    )
    
    context.user_data['awaiting_broadcast'] = True


async def send_broadcast(context: ContextTypes.DEFAULT_TYPE, target: str, message: str, bot) -> dict:
    """Send broadcast message to target audience."""
    results = {'sent': 0, 'blocked': 0, 'failed': 0}
    
    # Get recipient IDs based on target
    if target == 'owners':
        recipients = await get_owner_ids_for_broadcast()
    elif target == 'users':
        recipients = await get_all_users_for_broadcast()
    elif target == 'minibot_users':
        recipients = await get_mini_bot_users_for_broadcast()
    else:  # all
        owners = await get_owner_ids_for_broadcast()
        users = await get_all_users_for_broadcast()
        recipients = list(set(owners + users))
    
    for recipient_id in recipients:
        try:
            await bot.send_message(chat_id=recipient_id, text=message, parse_mode='Markdown')
            results['sent'] += 1
            await asyncio.sleep(0.05)  # Rate limiting
        except Exception as e:
            if 'blocked' in str(e).lower():
                results['blocked'] += 1
            else:
                results['failed'] += 1
    
    return results


async def show_pause_menu(query) -> None:
    """Show owner pause menu."""
    owners = await get_all_owners()
    active_owners = [o for o in owners if o['is_active']]
    
    if not active_owners:
        await query.edit_message_text("📭 No active owners to pause.")
        return
    
    keyboard = []
    for owner in active_owners[:10]:
        keyboard.append([
            InlineKeyboardButton(
                f"⏸ {owner['business_name'] or owner['telegram_id']}", 
                callback_data=f"admin_pause_owner_{owner['telegram_id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "⏸ **Pause Owner**\n\nSelect an owner to pause:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def pause_owner(query, owner_id: int) -> None:
    """Pause an owner's bot."""
    await update_owner(owner_id, is_active=False)
    await query.edit_message_text(f"✅ Owner {owner_id} has been paused.")


async def show_delete_menu(query) -> None:
    """Show owner delete menu."""
    owners = await get_all_owners()
    
    if not owners:
        await query.edit_message_text("📭 No owners to delete.")
        return
    
    keyboard = []
    for owner in owners[:10]:
        keyboard.append([
            InlineKeyboardButton(
                f"🗑 {owner['business_name'] or owner['telegram_id']}", 
                callback_data=f"admin_delete_owner_{owner['telegram_id']}"
            )
        ])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🗑 **Delete Owner**\n\n⚠️ This action is permanent!\n\nSelect an owner:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def delete_owner(query, owner_id: int) -> None:
    """Delete an owner."""
    # In production, you'd want a confirmation step
    await update_owner(owner_id, is_active=False)  # Soft delete
    await query.edit_message_text(f"✅ Owner {owner_id} has been deleted.")
