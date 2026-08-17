"""
Script to initialize the database with default news sources from TZ.
Run this once to populate the database with configured sources.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database.db_manager import DatabaseManager


async def init_default_sources():
    """Initialize database with default sources from TZ."""
    
    db = DatabaseManager()
    await db.connect()
    
    # Website sources from TZ
    websites = [
        {
            'url': 'https://dzen.ru/proplast',
            'title': 'Dzen Proplast (Сравнение цен на полимеры)',
            'note': 'Берет 1 новость с заголовком "1 неделю назад Сравнение цен на полимеры за"'
        },
        {
            'url': 'https://dzen.ru/okstanok',
            'title': 'Dzen Okstanok',
            'note': 'Берет последнюю новость'
        },
        {
            'url': 'https://polymerbranch.com/news/',
            'title': 'Polymer Branch News',
            'note': 'Берет последние 3 новости'
        },
        {
            'url': 'https://plastinfo.ru/information/news/',
            'title': 'Plastinfo News',
            'note': 'Берет последние 3 новости'
        },
        {
            'url': 'https://e-plastic.ru/news/?PAGEN_1=2&SIZEN_1=20',
            'title': 'E-Plastic News',
            'note': 'Берет последние 3 новости'
        },
        {
            'url': 'https://news.unipack.ru/',
            'title': 'Unipack News',
            'note': 'Берет последние 3 новости'
        }
    ]
    
    # Telegram channels from TZ
    telegram_channels = [
        {'url': '@plastinforu', 'title': 'Пластинфо'},
        {'url': '@plasticsmagazine', 'title': 'Plastics Magazine'},
        {'url': '@unipacknews', 'title': 'Unipack News'},
        {'url': '@naukasibur', 'title': 'Наука Сибур'},
        {'url': '@Poly_Pro', 'title': 'Poly Pro'},
        {'url': '@polymerbranch', 'title': 'Polymer Branch'}
    ]
    
    print("=" * 60)
    print("Инициализация базы данных источниками новостей")
    print("=" * 60)
    
    # Add website sources
    print("\n📰 Добавляю веб-сайты:")
    for site in websites:
        success = await db.add_source(
            url=site['url'],
            source_type='website',
            title=site['title']
        )
        status = "✅" if success else "⚠️ (уже существует)"
        print(f"  {status} {site['title']} ({site['url']})")
        if site.get('note'):
            print(f"      📝 {site['note']}")
    
    # Add Telegram channels
    print("\n✈️ Добавляю Telegram каналы:")
    for channel in telegram_channels:
        success = await db.add_source(
            url=channel['url'],
            source_type='telegram',
            title=channel['title']
        )
        status = "✅" if success else "⚠️ (уже существует)"
        print(f"  {status} {channel['title']} ({channel['url']})")
    
    # Show statistics
    print("\n" + "=" * 60)
    stats = await db.get_stats()
    print(f"📊 Статистика:")
    print(f"   Активных источников: {stats['active_sources']}")
    print(f"   Расписаний: {stats['active_schedules']}")
    print(f"   Всего новостей в истории: {stats['total_news']}")
    print(f"   Обработано новостей: {stats['processed_news']}")
    print("=" * 60)
    
    # Add default schedule (Monday at 9:00 AM)
    print("\n⏰ Добавляю расписание по умолчанию (Понедельник, 09:00):")
    success = await db.add_schedule(day_of_week=0, hour=9, minute=0)
    if success:
        print("  ✅ Расписание добавлено")
    else:
        print("  ⚠️ Расписание уже существует")
    
    schedules = await db.get_schedules()
    if schedules:
        print("\n📅 Текущие расписания:")
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        for sched in schedules:
            print(f"   • {days[sched['day_of_week']]} {sched['hour']:02d}:{sched['minute']:02d}")
    
    await db.disconnect()
    
    print("\n✅ Инициализация завершена!")
    print("\n📝 Следующие шаги:")
    print("   1. Настройте .env файл с вашими API ключами")
    print("   2. Запустите бота: python main.py")
    print("   3. Добавьте дополнительные источники через /add_source при необходимости")
    print("   4. Настройте расписание через /schedule")


if __name__ == '__main__':
    asyncio.run(init_default_sources())
