"""
Footer template for mini bot messages
"""

from config import FOOTER_TEXT


def add_footer(message: str) -> str:
    """Add ConnectProBot footer to message."""
    return f"{message}\n\n—\n{FOOTER_TEXT}"


def remove_footer(message: str) -> str:
    """Remove footer from message if present."""
    if FOOTER_TEXT in message:
        return message.replace(f"\n\n—\n{FOOTER_TEXT}", "")
    return message
