"""
Message Router Service for ConnectProBot
Handles message routing between users and owners
"""

import logging
from typing import Optional, Tuple
from telegram import Bot

from database import (
    get_owner, get_or_create_conversation, save_message,
    check_message_limit, increment_message_count
)
from templates.footer import add_footer
from config import FREE_MODE_MESSAGE_LIMIT

logger = logging.getLogger(__name__)


class MessageRouter:
    """Handles message routing between users and owners."""
    
    def __init__(self, main_bot: Bot):
        self.main_bot = main_bot
        self.mini_bots: dict = {}
    
    def register_mini_bot(self, owner_id: int, bot: Bot) -> None:
        """Register a mini bot for message routing."""
        self.mini_bots[owner_id] = bot
    
    def unregister_mini_bot(self, owner_id: int) -> None:
        """Unregister a mini bot."""
        self.mini_bots.pop(owner_id, None)
    
    async def route_user_message(
        self, 
        user_id: int, 
        user_name: str,
        owner_id: int, 
        message_text: str,
        message_id: int
    ) -> Tuple[bool, str]:
        """
        Route a message from user to owner.
        Returns (success, response_message).
        """
        owner = await get_owner(owner_id)
        
        if not owner:
            return False, "❌ This business is no longer available."
        
        if not owner['is_active']:
            return False, "❌ This business is currently inactive."
        
        # Check message limits for free mode
        if owner['bot_type'] == 'this_bot':
            can_send = await check_message_limit(user_id, owner_id, FREE_MODE_MESSAGE_LIMIT)
            if not can_send:
                return False, f"📫 Daily limit reached ({FREE_MODE_MESSAGE_LIMIT} messages)."
        
        # Save to database
        conversation = await get_or_create_conversation(user_id, owner_id, owner.get('bot_token'))
        await save_message(
            conversation_id=conversation['id'],
            sender_type='user',
            message_text=message_text,
            telegram_message_id=message_id
        )
        
        # Increment counter for free mode
        if owner['bot_type'] == 'this_bot':
            await increment_message_count(user_id, owner_id)
        
        # Forward to owner
        try:
            forward_text = (
                f"📩 **New Message**\n\n"
                f"From: {user_name}\n"
                f"Message: {message_text}\n\n"
                f"_Reply to respond_"
            )
            
            await self.main_bot.send_message(
                chat_id=owner_id,
                text=forward_text,
                parse_mode='Markdown'
            )
            
            return True, "✅ Message sent!"
            
        except Exception as e:
            logger.error(f"Failed to route message: {e}")
            return False, "❌ Failed to deliver. Try again."
    
    async def route_owner_reply(
        self,
        owner_id: int,
        user_id: int,
        message_text: str
    ) -> Tuple[bool, str]:
        """
        Route a reply from owner to user.
        Returns (success, response_message).
        """
        owner = await get_owner(owner_id)
        
        if not owner:
            return False, "❌ Owner not found."
        
        # Add footer for mini bots
        reply_text = message_text
        if owner['bot_type'] == 'own_bot':
            reply_text = add_footer(reply_text)
        
        try:
            # Use appropriate bot for reply
            if owner_id in self.mini_bots:
                bot = self.mini_bots[owner_id]
            else:
                bot = self.main_bot
            
            await bot.send_message(
                chat_id=user_id,
                text=f"📬 Reply from **{owner['business_name']}**:\n\n{reply_text}",
                parse_mode='Markdown'
            )
            
            # Save reply to database
            conversation = await get_or_create_conversation(user_id, owner_id)
            await save_message(
                conversation_id=conversation['id'],
                sender_type='owner',
                message_text=message_text
            )
            
            return True, "✅ Reply sent!"
            
        except Exception as e:
            logger.error(f"Failed to route reply: {e}")
            return False, "❌ Failed to send reply."


class MessageFilter:
    """Filters and categorizes messages."""
    
    CATEGORIES = ['order', 'support', 'query', 'other']
    
    KEYWORDS = {
        'order': ['order', 'buy', 'purchase', 'price', 'cost', 'payment'],
        'support': ['help', 'issue', 'problem', 'error', 'broken', 'fix'],
        'query': ['question', 'ask', 'how', 'what', 'when', 'where', 'why'],
    }
    
    @classmethod
    def categorize(cls, message_text: str) -> str:
        """Categorize a message based on keywords."""
        text_lower = message_text.lower()
        
        for category, keywords in cls.KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return category
        
        return 'other'
    
    @classmethod
    def filter_messages(cls, messages: list, category: str) -> list:
        """Filter messages by category."""
        if category == 'all':
            return messages
        
        return [
            msg for msg in messages 
            if cls.categorize(msg.get('message_text', '')) == category
        ]
