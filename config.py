"""
Configuration settings for ConnectProBot
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
BOT_USERNAME = "@connectsprobot"

# Admin Configuration
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "5402727692").split(",")]

# Database Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "")

# Feature Limits
FREE_MODE_MESSAGE_LIMIT = 2  # Messages per user per day
FREE_MODE_START_HOUR = 9  # 9:00 AM
FREE_MODE_END_HOUR = 23  # 11:50 PM (23:50)
FREE_MODE_END_MINUTE = 50

# Trial Configuration
TRIAL_DAYS = 120  # 4 months

# Cleanup Configuration
MESSAGE_RETENTION_DAYS = 72  # Delete messages after 72 days

# Categories
CATEGORIES = ["Tech", "Education", "E-commerce", "Other"]

# Templates
FOOTER_TEXT = "This Bot was made using @Connectsprobot"
