"""
Telegram Bot Module
Handles Telegram bot interactions, scheduling, and user interface
"""

import logging
import asyncio
from datetime import datetime
from typing import List, Optional
from telethon import TelegramClient, events
from telethon.tl.types import Message
from telethon.utils import get_display_name
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_USER_ID, SCHEDULE_DAY_OF_WEEK, 
    SCHEDULE_HOUR, SCHEDULE_MINUTE, NEWS_SOURCES, LOG_LEVEL
)
from news_collector import NewsCollector, NewsItem
from ai_processor import NewsProcessor

logger = logging.getLogger(__name__)


class NewsBot:
    """Main Telegram bot class for news collection and processing"""
    
    def __init__(self):
        self.bot_token = TELEGRAM_BOT_TOKEN
        self.admin_user_id = TELEGRAM_USER_ID
        
        # Initialize Telegram client for bot
        self.client = TelegramClient('news_bot_session', 20833406, 'c0d9f07b5a1e8c9d3f2b4a6e8d0c2b4a')
        
        # Initialize collectors and processors
        # Note: For Telegram channel reading, you need your own API credentials
        # Get them from https://my.telegram.org/apps
        self.news_collector = NewsCollector()  # Add TG API credentials if needed
        self.ai_processor = None  # Will be initialized with API keys
        
        self.scheduler = AsyncIOScheduler()
        self.current_news: List[NewsItem] = []
        self.pending_selection = False
        
        # Inline keyboard buttons cache
        self.selection_buttons = []
    
    async def start(self):
        """Start the bot"""
        
        # Initialize AI processor if API keys are available
        try:
            from config import TEXT_RU_API_KEY, OPENAI_API_KEY
            
            if OPENAI_API_KEY and OPENAI_API_KEY != "YOUR_OPENAI_API_KEY_HERE":
                self.ai_processor = NewsProcessor(
                    text_api_key=OPENAI_API_KEY,
                    image_api_key=OPENAI_API_KEY,
                    text_provider="openai",
                    image_provider="openai"
                )
                logger.info("AI Processor initialized with OpenAI")
            elif TEXT_RU_API_KEY and TEXT_RU_API_KEY != "YOUR_TEXT_RU_API_KEY_HERE":
                self.ai_processor = NewsProcessor(
                    text_api_key=TEXT_RU_API_KEY,
                    text_provider="text_ru"
                )
                logger.info("AI Processor initialized with Text.ru")
            else:
                logger.warning("No AI API keys configured. AI features will be disabled.")
        except Exception as e:
            logger.error(f"Error initializing AI processor: {e}")
        
        # Setup scheduler
        self.setup_scheduler()
        
        # Start bot
        await self.client.start(bot_token=self.bot_token)
        logger.info("Bot started successfully")
        
        # Register event handlers
        self.register_handlers()
        
        # Start scheduler
        self.scheduler.start()
        logger.info("Scheduler started")
        
        # Run until disconnected
        await self.client.run_until_disconnected()
    
    def setup_scheduler(self):
        """Setup automatic news collection schedule"""
        
        # Parse day of week
        day_map = {
            'mon': 'mon', 'tue': 'tue', 'wed': 'wed', 'thu': 'thu',
            'fri': 'fri', 'sat': 'sat', 'sun': 'sun'
        }
        
        days = [day_map.get(d.strip().lower(), d.strip().lower()) 
                for d in SCHEDULE_DAY_OF_WEEK.split(',')]
        day_of_week = ','.join(days)
        
        # Add scheduled job
        self.scheduler.add_job(
            self.scheduled_news_collection,
            trigger=CronTrigger(day_of_week=day_of_week, hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE),
            id='daily_news_collection',
            name='Daily News Collection',
            replace_existing=True
        )
        
        logger.info(f"Scheduled news collection: {day_of_week} at {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d}")
    
    async def scheduled_news_collection(self):
        """Scheduled task to collect and present news"""
        
        logger.info("Starting scheduled news collection")
        
        try:
            # Collect news
            self.current_news = await self.news_collector.collect_all_news(NEWS_SOURCES)
            
            if not self.current_news:
                await self.client.send_message(
                    self.admin_user_id,
                    "❌ Не удалось собрать новости. Проверьте логи."
                )
                return
            
            # Send report to user
            await self.send_news_report()
            
        except Exception as e:
            logger.error(f"Error in scheduled news collection: {e}")
            await self.client.send_message(
                self.admin_user_id,
                f"❌ Ошибка при сборе новостей: {str(e)}"
            )
    
    async def send_news_report(self):
        """Send news report with selection buttons"""
        
        if not self.current_news:
            return
        
        # Create summary message
        summary = f"📰 <b>Собрано новостей: {len(self.current_news)}</b>\n\n"
        summary += f"🕒 <b>Время сбора:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        
        # Group by source
        news_by_source = {}
        for i, news in enumerate(self.current_news):
            source = news.source
            if source not in news_by_source:
                news_by_source[source] = []
            news_by_source[source].append((i, news))
        
        for source, items in news_by_source.items():
            summary += f"\n<b>{source}</b> ({len(items)}):\n"
            for idx, news in items[:3]:  # Show first 3 from each source
                title = news.title[:80] + "..." if len(news.title) > 80 else news.title
                summary += f"  {idx + 1}. {title}\n"
        
        summary += "\n\nВыберите интересные новости для обработки (отправьте номера через запятую):"
        
        # Create inline keyboard with selection buttons
        from telethon.tl.types import KeyboardButtonInline, KeyboardButtonRow
        from telethon.tl.custom import Button
        
        # Create buttons in groups of 5
        buttons = []
        for i in range(0, min(len(self.current_news), 20), 5):
            row = []
            for j in range(i, min(i + 5, len(self.current_news))):
                row.append(Button.inline(f"{j + 1}", data=f"select_{j}".encode()))
            buttons.append(row)
        
        # Add "Select All" and "Process Selected" buttons
        buttons.append([Button.inline("✅ Выбрать все", data=b"select_all")])
        buttons.append([Button.inline("🚀 Обработать выбранные", data=b"process_selected")])
        
        # Send message
        await self.client.send_message(
            self.admin_user_id,
            summary,
            parse_mode='html',
            buttons=buttons,
            link_preview=False
        )
        
        self.pending_selection = True
    
    def register_handlers(self):
        """Register event handlers for bot interactions"""
        
        @self.client.on(events.NewMessage(pattern=r'^/start$', outgoing=True))
        async def handler_start(event):
            """Handle /start command"""
            await event.respond(
                "🤖 <b>News Bot запущен!</b>\n\n"
                "Команды:\n"
                "/start - Запустить бота\n"
                "/collect - Собрать новости вручную\n"
                "/status - Показать статус\n"
                "/help - Помощь",
                parse_mode='html'
            )
        
        @self.client.on(events.NewMessage(pattern=r'^/collect$', outgoing=True))
        async def handler_collect(event):
            """Handle manual news collection"""
            await event.respond("🔄 Начинаю сбор новостей...")
            await self.scheduled_news_collection()
        
        @self.client.on(events.NewMessage(pattern=r'^/status$', outgoing=True))
        async def handler_status(event):
            """Handle status command"""
            status = f"📊 <b>Статус бота:</b>\n\n"
            status += f"📰 Новостей собрано: {len(self.current_news)}\n"
            status += f"⏰ Следующий запуск: {SCHEDULE_DAY_OF_WEEK} в {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d}\n"
            status += f"🤖 AI процессор: {'✅ Активен' if self.ai_processor else '❌ Не настроен'}"
            
            await event.respond(status, parse_mode='html')
        
        @self.client.on(events.NewMessage(pattern=r'^/help$', outgoing=True))
        async def handler_help(event):
            """Handle help command"""
            help_text = """
🤖 <b>Помощь по News Bot</b>

Этот бот собирает новости из указанных источников и обрабатывает их с помощью ИИ.

<b>Как это работает:</b>
1. По расписанию бот собирает новости с сайтов и из Telegram-каналов
2. Вам приходит отчет со списком новостей
3. Вы выбираете интересные новости (кликом по кнопкам или отправкой номеров)
4. Бот отправляет выбранные новости на обработку ИИ:
   - Рерайтинг текста
   - Генерация иллюстрации
5. Вы получаете готовые посты с уникальным текстом и картинкой

<b>Источники новостей:</b>
- Сайты: Dzen, PolymerBranch, PlastInfo, E-Plastic, UniPack
- Telegram-каналы: 6 каналов по тематике полимеров и упаковки

<b>Настройка:</b>
Отредактируйте config.py для изменения:
- Расписания сбора
- Списка источников
- API ключей для ИИ

"""
            await event.respond(help_text, parse_mode='html')
        
        @self.client.on(events.CallbackQuery)
        async def handler_callback(event):
            """Handle inline button clicks"""
            
            data = event.data.decode()
            
            if data.startswith("select_"):
                if data == "select_all":
                    # Select all news
                    self.selected_indices = list(range(len(self.current_news)))
                    await event.answer("✅ Выбраны все новости", alert=True)
                else:
                    # Toggle single selection
                    idx = int(data.split("_")[1])
                    if not hasattr(self, 'selected_indices'):
                        self.selected_indices = []
                    
                    if idx in self.selected_indices:
                        self.selected_indices.remove(idx)
                        await event.answer(f"❌ Новость {idx + 1} отменена", alert=True)
                    else:
                        self.selected_indices.append(idx)
                        await event.answer(f"✅ Новость {idx + 1} выбрана", alert=True)
                
                # Update selection display
                selected_count = len(getattr(self, 'selected_indices', []))
                await event.edit(
                    f"📰 Выбрано новостей: {selected_count}\n\n"
                    f"Нажмите '🚀 Обработать выбранные' для продолжения",
                    buttons=[
                        [Button.inline("✅ Выбрать все", data=b"select_all")],
                        [Button.inline("🚀 Обработать выбранные", data=b"process_selected")]
                    ]
                )
            
            elif data == "process_selected":
                if not hasattr(self, 'selected_indices') or not self.selected_indices:
                    await event.answer("⚠️ Сначала выберите новости", alert=True)
                    return
                
                await event.answer("🔄 Начинаю обработку...", alert=True)
                await event.delete()
                
                # Process selected news
                await self.process_selected_news()
        
        @self.client.on(events.NewMessage(func=lambda e: e.is_private))
        async def handler_text_selection(event):
            """Handle text message with news indices"""
            
            if not self.pending_selection:
                return
            
            text = event.message.text.strip()
            
            try:
                # Parse indices (e.g., "1, 3, 5" or "1 3 5")
                indices = []
                for part in text.replace(',', ' ').split():
                    try:
                        idx = int(part) - 1  # Convert to 0-based
                        if 0 <= idx < len(self.current_news):
                            indices.append(idx)
                    except ValueError:
                        continue
                
                if indices:
                    self.selected_indices = indices
                    await event.respond(
                        f"✅ Выбрано новостей: {len(indices)}\n\n"
                        f"Отправьте /process для обработки или выберите другие новости."
                    )
                else:
                    await event.respond("⚠️ Неверный формат. Отправьте номера через запятую (например: 1, 3, 5)")
            
            except Exception as e:
                logger.error(f"Error parsing selection: {e}")
                await event.respond("⚠️ Ошибка при обработке выбора. Попробуйте еще раз.")
        
        @self.client.on(events.NewMessage(pattern=r'^/process$', outgoing=True))
        async def handler_process(event):
            """Handle manual process command"""
            if hasattr(self, 'selected_indices') and self.selected_indices:
                await event.respond("🔄 Начинаю обработку выбранных новостей...")
                await self.process_selected_news()
            else:
                await event.respond("⚠️ Нет выбранных новостей. Сначала соберите новости командой /collect")
    
    async def process_selected_news(self):
        """Process selected news with AI"""
        
        if not hasattr(self, 'selected_indices') or not self.selected_indices:
            return
        
        if not self.ai_processor:
            await self.client.send_message(
                self.admin_user_id,
                "❌ AI процессор не настроен. Добавьте API ключи в config.py"
            )
            return
        
        selected_count = len(self.selected_indices)
        await self.client.send_message(
            self.admin_user_id,
            f"🔄 Обрабатываю {selected_count} новостей...\n\n"
            f"Это может занять несколько минут."
        )
        
        # Process each selected news
        for idx in self.selected_indices:
            if 0 <= idx < len(self.current_news):
                news_item = self.current_news[idx]
                
                try:
                    # Process with AI
                    rewritten_text, image_url = await self.ai_processor.process_news(
                        news_item,
                        rewrite=True,
                        generate_image=True
                    )
                    
                    # Send result
                    result_message = f"📰 <b>Обработанная новость #{idx + 1}</b>\n\n"
                    
                    if rewritten_text:
                        result_message += f"{rewritten_text}\n\n"
                    
                    if news_item.url:
                        result_message += f"🔗 <a href='{news_item.url}'>Источник</a>\n"
                    
                    await self.client.send_message(
                        self.admin_user_id,
                        result_message,
                        parse_mode='html',
                        link_preview=True
                    )
                    
                    # Send image if generated
                    if image_url:
                        if image_url.startswith('http'):
                            # URL from DALL-E
                            await self.client.send_file(
                                self.admin_user_id,
                                image_url,
                                caption=f"🖼️ Иллюстрация для новости: {news_item.title[:50]}..."
                            )
                        else:
                            # Local file path
                            await self.client.send_file(
                                self.admin_user_id,
                                image_url,
                                caption=f"🖼️ Иллюстрация для новости"
                            )
                    
                    logger.info(f"Successfully processed news #{idx + 1}")
                    
                except Exception as e:
                    logger.error(f"Error processing news #{idx + 1}: {e}")
                    await self.client.send_message(
                        self.admin_user_id,
                        f"❌ Ошибка при обработке новости #{idx + 1}: {str(e)}"
                    )
        
        # Reset selection
        self.selected_indices = []
        
        await self.client.send_message(
            self.admin_user_id,
            "✅ Обработка завершена!"
        )


async def main():
    """Main entry point"""
    
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/bot.log'),
            logging.StreamHandler()
        ]
    )
    
    # Create and start bot
    bot = NewsBot()
    await bot.start()


if __name__ == '__main__':
    asyncio.run(main())
