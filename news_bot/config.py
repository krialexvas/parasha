"""
Configuration module for the news bot.
Loads environment variables and provides settings access.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent.absolute()

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))

# TEXT.ru API Configuration
TEXT_RU_API_KEY = os.getenv('TEXT_RU_API_KEY', '')

# Kandinsky API Configuration
KANDINSKY_API_KEY = os.getenv('KANDINSKY_API_KEY', '')
KANDINSKY_SECRET_KEY = os.getenv('KANDINSKY_SECRET_KEY', '')

# Telethon Configuration (for Telegram channel parsing)
TELETHON_API_ID = int(os.getenv('TELETHON_API_ID', '0'))
TELETHON_API_HASH = os.getenv('TELETHON_API_HASH', '')

# Database Configuration
DATABASE_PATH = os.getenv('DATABASE_PATH', str(BASE_DIR / 'news_bot.db'))

# Output Directory
OUTPUT_DIR = os.getenv('OUTPUT_DIR', str(BASE_DIR / 'output'))

# Parsing Limits
MAX_NEWS_PER_RUN = int(os.getenv('MAX_NEWS_PER_RUN', '20'))
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))

# Ensure output directory exists
Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


def validate_config():
    """Validate that all required configuration is present."""
    required_vars = {
        'TELEGRAM_BOT_TOKEN': TELEGRAM_BOT_TOKEN,
        'ADMIN_USER_ID': ADMIN_USER_ID,
        'TELETHON_API_ID': TELETHON_API_ID,
        'TELETHON_API_HASH': TELETHON_API_HASH,
    }
    
    missing = []
    for var_name, var_value in required_vars.items():
        if not var_value or var_value == 0:
            missing.append(var_name)
    
    if missing:
        raise ValueError(f"Missing required configuration: {', '.join(missing)}")
    
    return True
