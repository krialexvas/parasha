# Telegram News Bot

Бот для сбора новостей из Telegram-каналов и веб-сайтов, с последующей обработкой через ИИ (рерайтинг текста и генерация изображений).

## Возможности

- 📰 Автоматический сбор новостей по расписанию
- 🔍 Источники: 6 сайтов + 6 Telegram-каналов
- 🤖 Обработка через ИИ:
  - Рерайтинг текста (OpenAI GPT или Text.ru)
  - Генерация изображений (DALL-E 3 или Stability AI)
- ⏰ Гибкое расписание (дни недели, время)
- 💬 Удобный интерфейс в Telegram с кнопками выбора

## Установка

### 1. Клонируйте репозиторий

```bash
cd news_bot
```

### 2. Установите зависимости

```bash
pip install -r requirements.txt
```

### 3. Настройте бота

#### Получите Telegram Bot Token
1. Откройте @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте полученный токен

#### Получите Telegram API Credentials (для чтения каналов)
1. Перейдите на https://my.telegram.org/apps
2. Войдите под своим аккаунтом
3. Создайте новое приложение
4. Скопируйте `API ID` и `API Hash`

#### Получите API ключи для ИИ

**Вариант A: OpenAI (рекомендуется)**
- Зарегистрируйтесь на https://platform.openai.com
- Создайте API ключ в разделе API Keys
- Поддерживается: GPT-4o-mini (рерайтинг) + DALL-E 3 (изображения)

**Вариант B: Text.ru + другой сервис для изображений**
- Зарегистрируйтесь на https://text.ru/apikey
- Получите API ключ
- Для изображений используйте Stability AI или другой сервис

### 4. Отредактируйте config.py

Откройте файл `config.py` и заполните:

```python
# Telegram Bot Settings
TELEGRAM_BOT_TOKEN = "ваш_токен_бота"
TELEGRAM_USER_ID = ваш_user_id  # Числовой ID вашего аккаунта

# Telegram API (для чтения каналов)
TG_API_ID = ваш_api_id
TG_API_HASH = "ваш_api_hash"

# AI API Settings
OPENAI_API_KEY = "ваш_openai_api_key"  # Рекомендуется
# ИЛИ
TEXT_RU_API_KEY = "ваш_text_ru_api_key"

# Scheduler Settings
SCHEDULE_DAY_OF_WEEK = "mon,wed,fri"  # Дни недели
SCHEDULE_HOUR = 10  # Час (24-часовой формат)
SCHEDULE_MINUTE = 0  # Минуты
```

#### Как узнать свой Telegram User ID:
1. Отправьте сообщение боту @userinfobot
2. Он ответит вашим числовым ID

## Запуск

### Обычный запуск

```bash
python bot.py
```

### Запуск в фоне (Linux/Mac)

```bash
nohup python bot.py > bot.log 2>&1 &
```

### Запуск в Windows (фон)

Создайте файл `start_bot.bat`:
```batch
@echo off
start /B python bot.py
exit
```

## Использование

### Команды бота

- `/start` - Запустить бота
- `/collect` - Собрать новости вручную
- `/status` - Показать статус
- `/help` - Помощь

### Рабочий процесс

1. **Автоматический сбор**: По расписанию бот собирает новости
2. **Отчет**: Вам приходит список собранных новостей
3. **Выбор**: Кликайте по кнопкам или отправьте номера (1, 3, 5)
4. **Обработка**: Нажмите "🚀 Обработать выбранные"
5. **Результат**: Получите рерайтнутый текст + изображение

## Источники новостей

### Сайты
1. https://dzen.ru/proplast (1 новость с фильтром)
2. https://dzen.ru/okstanok (последняя новость)
3. https://polymerbranch.com/news/ (3 новости)
4. https://plastinfo.ru/information/news/ (3 новости)
5. https://e-plastic.ru/news/ (3 новости)
6. https://news.unipack.ru/ (3 новости)

### Telegram-каналы
1. @plastinforu (5 новостей)
2. @plasticsmagazine (5 новостей)
3. @unipacknews (5 новостей)
4. @naukasibur (5 новостей)
5. @Poly_Pro (5 новостей)
6. @polymerbranch (5 новостей)

## Структура проекта

```
news_bot/
├── config.py           # Конфигурация
├── news_collector.py   # Сбор новостей
├── ai_processor.py     # ИИ обработка
├── bot.py              # Telegram бот
├── requirements.txt    # Зависимости
├── logs/               # Логи
│   └── bot.log
└── images/             # Сгенерированные изображения
```

## Настройка расписания

В `config.py` измените:

```python
# Каждый день в 9:00
SCHEDULE_DAY_OF_WEEK = "mon,tue,wed,thu,fri,sat,sun"
SCHEDULE_HOUR = 9
SCHEDULE_MINUTE = 0

# Только будни в 10:30
SCHEDULE_DAY_OF_WEEK = "mon,tue,wed,thu,fri"
SCHEDULE_HOUR = 10
SCHEDULE_MINUTE = 30

# Понедельник и четверг в 14:00
SCHEDULE_DAY_OF_WEEK = "mon,thu"
SCHEDULE_HOUR = 14
SCHEDULE_MINUTE = 0
```

Допустимые значения дней: `mon, tue, wed, thu, fri, sat, sun`

## Troubleshooting

### Бот не запускается
- Проверьте правильность токена в `config.py`
- Убедитесь, что все зависимости установлены: `pip install -r requirements.txt`

### Не собираются новости с сайтов
- Проверьте доступность сайтов
- Некоторые сайты могут блокировать парсинг
- Смотрите логи в `logs/bot.log`

### Не читаются Telegram-каналы
- Убедитесь, что указали `TG_API_ID` и `TG_API_HASH`
- Проверьте, что каналы публичные или бот добавлен в них

### Ошибки ИИ обработки
- Проверьте баланс API ключа
- Убедитесь, что ключ активен
- Смотрите детали ошибки в логах

## Рекомендации

1. **Используйте OpenAI API** для лучшего качества рерайтинга
2. **Настройте логирование** для отслеживания работы
3. **Запустите бота на сервере** или всегда включенном ПК
4. **Регулярно проверяйте логи** для своевременного обнаружения проблем

## Лицензия

MIT License
