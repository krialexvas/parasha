"""
Main Telegram bot for news collection and AI processing.
Provides interactive interface for managing sources, schedules, and processing news.
"""
import asyncio
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

from config import (
    TELEGRAM_BOT_TOKEN,
    ADMIN_USER_ID,
    validate_config
)
from database.db_manager import DatabaseManager
from parser.telegram_parser import TelegramParser
from parser.web_parser import WebParser
from ai_services.rewriter import TextRewriter
from ai_services.image_generator import ImageGenerator
from storage.file_manager import FileManager
from scheduler.job_scheduler import JobScheduler

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
ADD_SOURCE_TYPE, ADD_SOURCE_URL, ADD_SOURCE_TITLE = range(3)
SCHEDULE_DAY, SCHEDULE_TIME = range(2)


class NewsBot:
    """Main bot class coordinating all components."""
    
    def __init__(self):
        self.db: Optional[DatabaseManager] = None
        self.tg_parser: Optional[TelegramParser] = None
        self.web_parser: Optional[WebParser] = None
        self.rewriter: Optional[TextRewriter] = None
        self.image_gen: Optional[ImageGenerator] = None
        self.file_manager: Optional[FileManager] = None
        self.scheduler: Optional[JobScheduler] = None
        
        # Current state
        self.current_news: List[Dict] = []
        self.selected_news_indices: List[int] = []
        
    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing bot components...")
        
        self.db = DatabaseManager()
        await self.db.connect()
        
        self.tg_parser = TelegramParser()
        self.web_parser = WebParser()
        self.rewriter = TextRewriter()
        self.image_gen = ImageGenerator()
        self.file_manager = FileManager()
        
        self.scheduler = JobScheduler()
        self.scheduler.initialize(self.db, self.run_scheduled_parse)
        
        logger.info("All components initialized successfully")
    
    async def shutdown(self):
        """Shutdown all components gracefully."""
        logger.info("Shutting down bot components...")
        
        if self.tg_parser:
            await self.tg_parser.disconnect()
        if self.web_parser:
            await self.web_parser.disconnect()
        if self.rewriter:
            await self.rewriter.disconnect()
        if self.image_gen:
            await self.image_gen.disconnect()
        if self.db:
            await self.db.disconnect()
        if self.scheduler:
            self.scheduler.stop()
        
        logger.info("All components shut down")
    
    async def run_scheduled_parse(self):
        """Run news parsing on schedule (called by scheduler)."""
        logger.info("Running scheduled news parse")
        
        # This would need to be integrated with the bot's message sending
        # For now, just log it
        await self.parse_all_sources(send_report=False)
    
    async def parse_all_sources(self, send_report: bool = True) -> List[Dict]:
        """
        Parse all configured sources.
        
        Args:
            send_report: Whether to send report to user
            
        Returns:
            List of collected news items
        """
        all_news = []
        
        # Get sources from database
        tg_channels = await self.db.get_telegram_channels()
        websites = await self.db.get_websites()
        
        logger.info(f"Parsing {len(tg_channels)} Telegram channels and {len(websites)} websites")
        
        # Parse Telegram channels
        if tg_channels:
            try:
                tg_news = await self.tg_parser.parse_channels(tg_channels, hours_back=24)
                all_news.extend(tg_news)
                logger.info(f"Collected {len(tg_news)} news from Telegram")
            except Exception as e:
                logger.error(f"Error parsing Telegram channels: {str(e)}")
        
        # Parse websites
        if websites:
            try:
                web_news = await self.web_parser.parse_sites(websites, hours_back=24)
                all_news.extend(web_news)
                logger.info(f"Collected {len(web_news)} news from websites")
            except Exception as e:
                logger.error(f"Error parsing websites: {str(e)}")
        
        # Store in current state
        self.current_news = all_news[:20]  # Limit to 20
        
        return self.current_news
    
    # ==================== BOT COMMAND HANDLERS ====================
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_text = (
            "🤖 **Бот для сбора и обработки новостей**\n\n"
            "Я умею:\n"
            "• Собирать новости из Telegram каналов и сайтов\n"
            "• Делать рерайт текстов через ИИ\n"
            "• Генерировать иллюстрации к новостям\n"
            "• Сохранять результаты в удобном формате\n\n"
            "**Доступные команды:**\n"
            "/add_source - Добавить источник новостей\n"
            "/list_sources - Показать все источники\n"
            "/remove_source - Удалить источник\n"
            "/schedule - Настроить расписание\n"
            "/parse_now - Запустить сбор новостей вручную\n"
            "/settings - Настройки бота\n"
            "/help - Помощь"
        )
        
        keyboard = [
            [InlineKeyboardButton("➕ Добавить источник", callback_data="add_source")],
            [InlineKeyboardButton("📋 Список источников", callback_data="list_sources")],
            [InlineKeyboardButton("⏰ Расписание", callback_data="schedule")],
            [InlineKeyboardButton("🔄 Собрать новости", callback_data="parse_now")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def add_source_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start adding a new source."""
        keyboard = [
            [InlineKeyboardButton("Telegram канал", callback_data="source_tg")],
            [InlineKeyboardButton("Веб-сайт", callback_data="source_web")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Выберите тип источника:",
            reply_markup=reply_markup
        )
        
        return ADD_SOURCE_TYPE
    
    async def add_source_type_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle source type selection."""
        query = update.callback_query
        await query.answer()
        
        context.user_data['source_type'] = 'telegram' if query.data == 'source_tg' else 'website'
        
        await query.edit_message_text(
            f"Отлично! Теперь отправьте {'username канала (например, @durov)' if context.user_data['source_type'] == 'telegram' else 'URL сайта (например, https://example.com/news)'}:"
        )
        
        return ADD_SOURCE_URL
    
    async def add_source_url_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle source URL/username input."""
        url = update.message.text.strip()
        context.user_data['source_url'] = url
        
        await update.message.reply_text(
            "Необязательно: Введите название источника (или пропустите /skip):"
        )
        
        return ADD_SOURCE_TITLE
    
    async def add_source_title_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle source title input or skip."""
        text = update.message.text.strip()
        
        if text.lower() == '/skip':
            title = None
        else:
            title = text
        
        # Add to database
        success = await self.db.add_source(
            url=context.user_data['source_url'],
            source_type=context.user_data['source_type'],
            title=title
        )
        
        if success:
            await update.message.reply_text(
                f"✅ Источник успешно добавлен!\n\n"
                f"Тип: {context.user_data['source_type']}\n"
                f"URL: {context.user_data['source_url']}" +
                (f"\nНазвание: {title}" if title else "")
            )
        else:
            await update.message.reply_text(
                "❌ Не удалось добавить источник. Возможно, он уже существует."
            )
        
        context.user_data.clear()
        return ConversationHandler.END
    
    async def cancel_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel current conversation."""
        context.user_data.clear()
        await update.message.reply_text("Операция отменена.")
        return ConversationHandler.END
    
    async def list_sources(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show all configured sources."""
        sources = await self.db.get_sources(active_only=False)
        
        if not sources:
            await update.message.reply_text("📭 Источники пока не добавлены.")
            return
        
        text = "📚 **Ваши источники новостей:**\n\n"
        
        for i, source in enumerate(sources, 1):
            status = "✅" if source['is_active'] else "❌"
            source_type = "TG" if source['source_type'] == 'telegram' else "WEB"
            text += f"{i}. {status} [{source_type}] {source['url']}"
            if source['title']:
                text += f" - {source['title']}"
            text += f"\n   ID: {source['id']}\n\n"
        
        text += "\nДля удаления отправьте /remove_source <ID>"
        
        await update.message.reply_text(text, parse_mode='Markdown')
    
    async def remove_source(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove a source by ID."""
        try:
            if context.args:
                source_id = int(context.args[0])
                success = await self.db.remove_source(source_id)
                
                if success:
                    await update.message.reply_text(f"✅ Источник {source_id} удален.")
                    
                    # Remove from scheduler if needed
                    job_id = f"schedule_{source_id}"
                    if self.scheduler:
                        self.scheduler.remove_job(job_id)
                else:
                    await update.message.reply_text("❌ Не удалось удалить источник.")
            else:
                await update.message.reply_text("Используйте: /remove_source <ID>")
        except ValueError:
            await update.message.reply_text("❌ ID должен быть числом.")
    
    async def schedule_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start setting up a schedule."""
        keyboard = [
            [InlineKeyboardButton("Понедельник", callback_data="day_0")],
            [InlineKeyboardButton("Вторник", callback_data="day_1")],
            [InlineKeyboardButton("Среда", callback_data="day_2")],
            [InlineKeyboardButton("Четверг", callback_data="day_3")],
            [InlineKeyboardButton("Пятница", callback_data="day_4")],
            [InlineKeyboardButton("Суббота", callback_data="day_5")],
            [InlineKeyboardButton("Воскресенье", callback_data="day_6")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "Выберите день недели для автоматического сбора новостей:",
            reply_markup=reply_markup
        )
        
        return SCHEDULE_DAY
    
    async def schedule_day_selected(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle day selection."""
        query = update.callback_query
        await query.answer()
        
        day_num = int(query.data.split('_')[1])
        context.user_data['schedule_day'] = day_num
        
        days = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
        
        await query.edit_message_text(
            f"{days[day_num]} выбран.\n\n"
            "Теперь отправьте время в формате ЧЧ:ММ (например, 09:00 или 18:30):"
        )
        
        return SCHEDULE_TIME
    
    async def schedule_time_received(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle time input."""
        time_text = update.message.text.strip()
        
        try:
            hour, minute = map(int, time_text.split(':'))
            
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                raise ValueError()
            
            # Add to database
            success = await self.db.add_schedule(
                day_of_week=context.user_data['schedule_day'],
                hour=hour,
                minute=minute
            )
            
            if success:
                # Add to scheduler
                if self.scheduler:
                    self.scheduler.add_job(
                        day_of_week=context.user_data['schedule_day'],
                        hour=hour,
                        minute=minute
                    )
                
                days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
                await update.message.reply_text(
                    f"✅ Расписание добавлено!\n\n"
                    f"День: {days[context.user_data['schedule_day']]}\n"
                    f"Время: {hour:02d}:{minute:02d}\n\n"
                    f"Теперь бот будет автоматически собирать новости в это время."
                )
            else:
                await update.message.reply_text("❌ Не удалось добавить расписание.")
        
        except (ValueError, IndexError):
            await update.message.reply_text(
                "❌ Неверный формат времени. Используйте ЧЧ:ММ (например, 09:00)"
            )
        
        context.user_data.clear()
        return ConversationHandler.END
    
    async def parse_now(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Manually trigger news parsing."""
        await update.message.reply_text("🔄 Начинаю сбор новостей...")
        
        news = await self.parse_all_sources(send_report=True)
        
        if not news:
            await update.message.reply_text("❌ Новости не найдены. Проверьте источники.")
            return
        
        # Show news selection interface
        await self.show_news_selection(update, news)
    
    async def show_news_selection(self, update: Update, news: List[Dict]):
        """Show news items for selection."""
        text = f"📰 **Найдено новостей: {len(news)}**\n\n"
        text += "Выберите интересные новости для обработки (отправьте номера через запятую):\n\n"
        
        for i, item in enumerate(news[:10], 1):  # Show first 10
            source_type = "TG" if item['source_type'] == 'telegram' else "WEB"
            text += f"{i}. [{source_type}] {item['title'][:80]}...\n"
            text += f"   Дата: {item['date'][:16]}\n\n"
        
        if len(news) > 10:
            text += f"... и еще {len(news) - 10} новостей\n\n"
        
        text += "Пример: 1, 3, 5 или 'все' для выбора всех"
        
        keyboard = [
            [InlineKeyboardButton("✅ Обработать выбранные", callback_data="process_selected")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_news_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user's news selection."""
        selection = update.message.text.strip().lower()
        
        if selection == 'все' or selection == 'all':
            self.selected_news_indices = list(range(len(self.current_news)))
        else:
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(',')]
                self.selected_news_indices = [i for i in indices if 0 <= i < len(self.current_news)]
            except ValueError:
                await update.message.reply_text(
                    "❌ Неверный формат. Отправьте номера через запятую (например: 1, 3, 5)"
                )
                return
        
        if not self.selected_news_indices:
            await update.message.reply_text("❌ Не выбрано ни одной новости.")
            return
        
        await update.message.reply_text(
            f"✅ Выбрано новостей: {len(self.selected_news_indices)}\n\n"
            "Начинаю обработку (рерайт + генерация изображений)..."
        )
        
        # Process selected news
        await self.process_selected_news(update)
    
    async def process_selected_news(self, update: Update):
        """Process selected news items through AI services."""
        processed_count = 0
        
        for idx in self.selected_news_indices:
            if idx >= len(self.current_news):
                continue
            
            news_item = self.current_news[idx]
            
            await update.message.reply_text(
                f"🔄 Обрабатываю: {news_item['title'][:50]}..."
            )
            
            try:
                # Rewrite text
                rewrite_result = await self.rewriter.rewrite_news_article(
                    title=news_item['title'],
                    content=news_item['content'],
                    style='news'
                )
                
                if not rewrite_result.get('success'):
                    await update.message.reply_text(f"❌ Ошибка рерайта: {news_item['title'][:50]}")
                    continue
                
                # Generate image
                image_bytes = await self.image_gen.generate_news_illustration(
                    title=rewrite_result['title'],
                    content=rewrite_result['content']
                )
                
                # Save to file system
                save_result = self.file_manager.save_complete_news(
                    parse_date=datetime.now(),
                    title=rewrite_result['title'],
                    content=rewrite_result['content'],
                    image_bytes=image_bytes,
                    metadata={
                        'source': news_item['source'],
                        'date': news_item['date'],
                        'link': news_item['link'],
                        'original_title': news_item['title']
                    }
                )
                
                if save_result['success']:
                    processed_count += 1
                    
                    # Send result to user
                    caption = (
                        f"✅ **{rewrite_result['title']}**\n\n"
                        f"Источник: {news_item['source']}\n"
                        f"Папка: {save_result['folder']}"
                    )
                    
                    if image_bytes and save_result['image']:
                        # Send image with caption
                        await update.message.reply_photo(
                            photo=image_bytes,
                            caption=caption,
                            parse_mode='Markdown'
                        )
                        
                        # Send document
                        if save_result['document']:
                            doc_path = Path(save_result['document'])
                            await update.message.reply_document(
                                document=open(doc_path, 'rb'),
                                filename=f"{doc_path.stem}.docx",
                                caption="📄 Word документ с новостью"
                            )
                    else:
                        await update.message.reply_text(caption, parse_mode='Markdown')
                
            except Exception as e:
                logger.error(f"Error processing news: {str(e)}")
                await update.message.reply_text(
                    f"❌ Ошибка при обработке: {str(e)[:100]}"
                )
        
        await update.message.reply_text(
            f"🎉 Обработка завершена!\n\n"
            f"Успешно обработано: {processed_count} из {len(self.selected_news_indices)}\n"
            f"Файлы сохранены в папке: {self.file_manager.output_dir}"
        )
        
        # Clear selection
        self.selected_news_indices = []
    
    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show bot settings."""
        stats = await self.db.get_stats()
        
        text = "⚙️ **Настройки бота**\n\n"
        text += f"📊 Статистика:\n"
        text += f"• Активных источников: {stats['active_sources']}\n"
        text += f"• Расписаний: {stats['active_schedules']}\n"
        text += f"• Всего новостей: {stats['total_news']}\n"
        text += f"• Обработано новостей: {stats['processed_news']}\n\n"
        
        text += f"📁 Папка сохранения: {self.file_manager.output_dir}\n"
        
        keyboard = [
            [InlineKeyboardButton("🗑 Очистить старые новости", callback_data="cleanup_old")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help information."""
        help_text = (
            "📖 **Помощь по боту**\n\n"
            "**Быстрый старт:**\n"
            "1. Добавьте источники через /add_source\n"
            "2. Настройте расписание через /schedule\n"
            "3. Запустите сбор через /parse_now или дождитесь автозапуска\n"
            "4. Выберите интересные новости\n"
            "5. Получите готовые файлы с рерайтом и картинками\n\n"
            "**Команды:**\n"
            "/start - Главное меню\n"
            "/add_source - Добавить Telegram канал или сайт\n"
            "/list_sources - Показать все источники\n"
            "/remove_source <ID> - Удалить источник по ID\n"
            "/schedule - Настроить автозапуск по расписанию\n"
            "/parse_now - Собрать новости вручную\n"
            "/settings - Настройки и статистика\n"
            "/help - Эта справка\n\n"
            "**Стоимость API:**\n"
            "• TEXT.ru: ~0.3-0.5 руб за 1000 символов\n"
            "• Kandinsky: бесплатно (лимит ~10-20 в день) или ~$0.02-0.05 за изображение\n\n"
            "**Поддержка:** Свяжитесь с администратором при возникновении проблем."
        )
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks."""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        
        if data == 'add_source':
            await self.add_source_start(update, context)
        elif data == 'list_sources':
            await self.list_sources(update, context)
        elif data == 'schedule':
            await self.schedule_start(update, context)
        elif data == 'parse_now':
            await self.parse_now(update, context)
        elif data == 'process_selected':
            await self.process_selected_news(update)
        elif data == 'cleanup_old':
            count = self.file_manager.cleanup_old_news(days_to_keep=30)
            await query.edit_message_text(f"🗑 Удалено старых папок: {count}")
    
    def create_application(self) -> Application:
        """Create and configure the bot application."""
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("help", self.help_command))
        app.add_handler(CommandHandler("settings", self.settings_command))
        app.add_handler(CommandHandler("list_sources", self.list_sources))
        app.add_handler(CommandHandler("remove_source", self.remove_source))
        
        # Conversation handler for adding sources
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("add_source", self.add_source_start)],
            states={
                ADD_SOURCE_TYPE: [
                    CallbackQueryHandler(self.add_source_type_selected)
                ],
                ADD_SOURCE_URL: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_source_url_received)
                ],
                ADD_SOURCE_TITLE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_source_title_received),
                    CommandHandler("skip", self.add_source_title_received)
                ]
            },
            fallbacks=[CommandHandler("cancel", self.cancel_conversation)]
        )
        app.add_handler(conv_handler)
        
        # Conversation handler for scheduling
        schedule_handler = ConversationHandler(
            entry_points=[CommandHandler("schedule", self.schedule_start)],
            states={
                SCHEDULE_DAY: [
                    CallbackQueryHandler(self.schedule_day_selected)
                ],
                SCHEDULE_TIME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.schedule_time_received)
                ]
            },
            fallbacks=[CommandHandler("cancel", self.cancel_conversation)]
        )
        app.add_handler(schedule_handler)
        
        # Handler for news selection
        app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handle_news_selection
        ))
        
        # Handler for button callbacks
        app.add_handler(CallbackQueryHandler(self.button_callback))
        
        return app
    
    async def run(self):
        """Run the bot."""
        try:
            # Validate configuration
            validate_config()
            
            # Initialize components
            await self.initialize()
            
            # Start scheduler
            await self.scheduler.start()
            
            # Create and run application
            application = self.create_application()
            
            logger.info("Bot is starting...")
            await application.initialize()
            await application.start()
            await application.updater.start_polling()
            
            logger.info("Bot is running. Press Ctrl+C to stop.")
            
            # Keep running until interrupted
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
        except Exception as e:
            logger.error(f"Bot error: {str(e)}")
            raise
        finally:
            await self.shutdown()


# Entry point
if __name__ == '__main__':
    bot = NewsBot()
    asyncio.run(bot.run())
