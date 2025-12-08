"""
Trial Service for ConnectProBot
Manages trial periods and expiration
"""

from datetime import datetime, timedelta
import logging

from config import TRIAL_DAYS
from database import get_all_owners, update_owner, check_trial_expired
from services.bot_factory import stop_mini_bot

logger = logging.getLogger(__name__)


async def check_all_trials() -> dict:
    """
    Check all owner trials and expire if needed.
    Returns summary of checked trials.
    """
    results = {
        'checked': 0,
        'expired': 0,
        'active': 0
    }
    
    owners = await get_all_owners()
    
    for owner in owners:
        if owner['bot_type'] != 'own_bot':
            continue
            
        results['checked'] += 1
        
        if await check_trial_expired(owner['telegram_id']):
            results['expired'] += 1
            # Stop the mini bot
            await stop_mini_bot(owner['telegram_id'])
            logger.info(f"Trial expired for owner {owner['telegram_id']}")
        else:
            results['active'] += 1
    
    return results


def get_trial_end_date(trial_start: datetime) -> datetime:
    """Calculate trial end date."""
    return trial_start + timedelta(days=TRIAL_DAYS)


def get_days_remaining(trial_start: datetime) -> int:
    """Get days remaining in trial."""
    if not trial_start:
        return 0
    
    end_date = get_trial_end_date(trial_start)
    remaining = (end_date - datetime.utcnow()).days
    return max(0, remaining)


async def notify_trial_expiring(owner_id: int, days_remaining: int, bot) -> bool:
    """Send trial expiration warning to owner."""
    try:
        if days_remaining == 7:
            message = (
                "⚠️ **Trial Expiring Soon!**\n\n"
                "Your 4-month free trial ends in 7 days.\n\n"
                "Subscription options coming soon!"
            )
        elif days_remaining == 1:
            message = (
                "🚨 **Last Day of Trial!**\n\n"
                "Your free trial ends tomorrow.\n\n"
                "After expiration, your mini bot will be paused.\n"
                "Subscription options coming soon!"
            )
        else:
            return False
        
        await bot.send_message(chat_id=owner_id, text=message, parse_mode='Markdown')
        return True
        
    except Exception as e:
        logger.error(f"Failed to send trial notification: {e}")
        return False


# Placeholder for future subscription system
SUBSCRIPTION_PLACEHOLDER = """
# SUBSCRIPTION SYSTEM - COMING SOON
# 
# When ready to implement subscriptions:
# 1. Add payment provider integration (Stripe, etc.)
# 2. Create subscription plans table
# 3. Add payment webhook handlers
# 4. Implement subscription status checks
# 5. Add billing management commands
#
# For now, trial_expired owners see:
# "Subscription Coming Soon. Please wait for update."
"""
