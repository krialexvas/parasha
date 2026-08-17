"""Parser module initialization."""
from .telegram_parser import TelegramParser
from .web_parser import WebParser

__all__ = ['TelegramParser', 'WebParser']
