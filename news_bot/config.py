# Telegram News Bot Configuration

# Telegram Bot Settings
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
TELEGRAM_USER_ID = 123456789  # Your numeric Telegram user ID (replace with actual number)

# Telegram API Credentials (for reading channels)
# Get these from https://my.telegram.org/apps
TG_API_ID = 12345678  # Replace with your API ID (number)
TG_API_HASH = "YOUR_TG_API_HASH_HERE"

# AI API Settings (using OpenAI recommended for best quality)
# Get OpenAI API key from https://platform.openai.com/api-keys
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY_HERE"  # For GPT-4o (rewriting) + DALL-E 3 (images)

# Alternative: Text.ru for text rewriting only
# Get API key from https://text.ru/apikey
TEXT_RU_API_KEY = "YOUR_TEXT_RU_API_KEY_HERE"

# For image generation alternatives:
# - Stability AI: https://stability.ai/api
# - Midjourney via third-party APIs
STABILITY_API_KEY = "YOUR_STABILITY_API_KEY_HERE"  # Optional

# Scheduler Settings (Cron-like format: day_of_week hour minute)
# Day of week: 0=Monday, 6=Sunday or use names: mon, tue, wed, thu, fri, sat, sun
SCHEDULE_DAY_OF_WEEK = "mon,wed,fri"  # Days to run
SCHEDULE_HOUR = 10  # Hour (24-hour format)
SCHEDULE_MINUTE = 0  # Minute

# News Source Settings
NEWS_SOURCES = {
    "websites": {
        "dzen_proplast": {
            "url": "https://dzen.ru/proplast",
            "count": 1,
            "filter_keyword": "Сравнение цен на полимеры за"
        },
        "dzen_okstanok": {
            "url": "https://dzen.ru/okstanok",
            "count": 1,
            "filter_keyword": None
        },
        "polymerbranch": {
            "url": "https://polymerbranch.com/news/",
            "count": 3,
            "filter_keyword": None
        },
        "plastinfo": {
            "url": "https://plastinfo.ru/information/news/",
            "count": 3,
            "filter_keyword": None
        },
        "e_plastic": {
            "url": "https://e-plastic.ru/news/?PAGEN_1=2&SIZEN_1=20",
            "count": 3,
            "filter_keyword": None
        },
        "unipack_news": {
            "url": "https://news.unipack.ru/",
            "count": 3,
            "filter_keyword": None
        }
    },
    "telegram_channels": {
        "plastinforu": {
            "username": "plastinforu",
            "count": 5
        },
        "plasticsmagazine": {
            "username": "plasticsmagazine",
            "count": 5
        },
        "unipacknews": {
            "username": "unipacknews",
            "count": 5
        },
        "naukasibur": {
            "username": "naukasibur",
            "count": 5
        },
        "Poly_Pro": {
            "username": "Poly_Pro",
            "count": 5
        },
        "polymerbranch": {
            "username": "polymerbranch",
            "count": 5
        }
    }
}

# Logging Settings
LOG_LEVEL = "INFO"
LOG_FILE = "logs/bot.log"
