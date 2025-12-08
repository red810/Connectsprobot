"""
Cleanup Service for ConnectProBot
Handles data retention and cleanup tasks
"""

import logging
from datetime import datetime, timedelta

from config import MESSAGE_RETENTION_DAYS
from database import cleanup_old_messages

logger = logging.getLogger(__name__)


async def run_daily_cleanup() -> dict:
    """
    Run daily cleanup tasks.
    Returns summary of cleanup actions.
    """
    results = {
        'messages_deleted': 0,
        'errors': []
    }
    
    try:
        # Delete old messages
        deleted_count = await cleanup_old_messages()
        results['messages_deleted'] = deleted_count
        logger.info(f"Daily cleanup: deleted {deleted_count} old messages")
        
    except Exception as e:
        error_msg = f"Message cleanup failed: {e}"
        results['errors'].append(error_msg)
        logger.error(error_msg)
    
    return results


def get_retention_date() -> datetime:
    """Get the date before which messages should be deleted."""
    return datetime.utcnow() - timedelta(days=MESSAGE_RETENTION_DAYS)


async def get_cleanup_stats() -> dict:
    """
    Get statistics about data that will be cleaned up.
    Useful for admin dashboard.
    """
    # This would query the database to show:
    # - Messages pending deletion
    # - Storage space that will be freed
    # - Last cleanup timestamp
    
    return {
        'retention_days': MESSAGE_RETENTION_DAYS,
        'retention_date': get_retention_date().isoformat(),
        'next_cleanup': 'Daily at 3:00 AM UTC'
    }


# Note: This service only deletes messages, NOT owners or subscriptions
# as per the requirements. Owner data is preserved indefinitely.
