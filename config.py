# -*- coding: utf-8 -*-
"""
Конфигурационный файл для Telegram бота
"""

import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Supabase Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# N8N Webhook Configuration - 3 отдельных вебхука
N8N_NICHE_WEBHOOK_URL = os.getenv('N8N_NICHE_WEBHOOK_URL')    # Определение ниши
N8N_TOPIC_WEBHOOK_URL = os.getenv('N8N_TOPIC_WEBHOOK_URL')    # Адаптация темы
N8N_POST_WEBHOOK_URL = os.getenv('N8N_POST_WEBHOOK_URL')      # Генерация поста

# Backward compatibility (если используется старая переменная)
if not N8N_NICHE_WEBHOOK_URL and os.getenv('N8N_WEBHOOK_URL'):
    N8N_NICHE_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL')
if not N8N_TOPIC_WEBHOOK_URL and os.getenv('N8N_WEBHOOK_URL'):
    N8N_TOPIC_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL')
if not N8N_POST_WEBHOOK_URL and os.getenv('N8N_WEBHOOK_URL'):
    N8N_POST_WEBHOOK_URL = os.getenv('N8N_WEBHOOK_URL')

# Bot Configuration
MAX_USERS = int(os.getenv('MAX_USERS', 1000))
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

# Admin Notifications
# Отправка уведомлений через основной бот в админский чат
ADMIN_CHAT_ID = os.getenv('ADMIN_CHAT_ID')
ENABLE_ADMIN_NOTIFICATIONS = os.getenv('ENABLE_ADMIN_NOTIFICATIONS', 'True').lower() == 'true'

# Database Tables
USERS_TABLE = 'users'
EMAILS_TABLE = 'allowed_emails'
DAILY_CONTENT_TABLE = 'daily_content'
USER_POST_LIMITS_TABLE = 'user_post_limits'
GENERATED_POSTS_TABLE = 'generated_posts'

# Bot States
class BotStates:
    WAITING_EMAIL = 'waiting_email'
    EMAIL_VERIFIED = 'email_verified'
    WAITING_NICHE_DESCRIPTION = 'waiting_niche_description'
    WAITING_NICHE_CONFIRMATION = 'waiting_niche_confirmation'
    NICHE_CONFIRMED = 'niche_confirmed'
    REGISTERED = 'registered'
    WAITING_POST_ANSWER = 'waiting_post_answer'
    POST_GENERATED = 'post_generated'

# Keyboard layouts
NICHE_CONFIRMATION_KEYBOARD = [
    ['✅ Верно', '🔄 Попробовать еще раз']
]

MAIN_MENU_KEYBOARD = [
    ['👤 Профиль']
]

PROFILE_KEYBOARD = [
    ['🎯 Изменить нишу'],
    ['⬅️ Назад']
]

# Ограничения
MAX_MESSAGE_LENGTH = 4000
MAX_VOICE_DURATION = 120  # секунд
MAX_EMAIL_LENGTH = 255
MAX_NICHE_LENGTH = 500
MAX_POST_ANSWER_LENGTH = 2000
MIN_POST_ANSWER_WORDS = 10
WEEKLY_POST_LIMIT = 10

# Настройки для голосовых сообщений
ALLOWED_VOICE_FORMATS = ['ogg', 'mp3', 'wav', 'm4a']
OPENAI_TRANSCRIPTION_MODEL = 'whisper-1'

# Настройки для напоминаний
REMINDER_TIME_HOUR = 9  # 9 утра
REMINDER_TIME_MINUTE = 0
TIMEZONE = 'Europe/Moscow'  # Можно настроить под нужную временную зону

# Regex для валидации email
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# Настройки для обработки ошибок
MAX_RETRIES = 3
RETRY_DELAY = 1  # секунд

# Настройки таймаутов для N8N
N8N_TOPIC_TIMEOUT = 180  # 3 минуты для адаптации темы
N8N_POST_TIMEOUT = 180   # 3 минуты для генерации поста
N8N_CONNECTION_TIMEOUT = 30  # таймаут подключения

# Логирование
LOG_LEVEL = 'INFO' if not DEBUG else 'DEBUG'
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
