# 🔄 Миграция на .env файл

Переход с config.env на стандартный .env файл для упрощения конфигурации.

## 🚀 Команды для сервера

### 1. Обновить код
```bash
cd /opt/innokentiy-telegram-bot
docker-compose down
git pull origin main
```

### 2. Создать .env файл
```bash
# Создать .env из примера
cp env.example .env

# Или конвертировать существующий config.env
cp config.env .env

# Отредактировать
nano .env
```

### 3. Заполнить .env (простой формат)
```env
# Telegram Bot Configuration
TELEGRAM_BOT_TOKEN=7951132986:AAG8YFtY9voIGJZIjNsvR0WzS-M-TYAdgKc

# Supabase Configuration  
SUPABASE_URL=http://localhost:8000
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYW5vbiIsImlzcyI6InN1cGFiYXNlIiwiaWF0IjoxNzU2NDYzNDkxLCJleHAiOjIwNzE4MjM0OTF9.jqg4Un7uoXl0cF3fbH2Q7sBYUVQFm5maFRQKPqeXyEw

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# N8N Webhook Configuration
N8N_NICHE_WEBHOOK_URL=http://localhost:5678/webhook/niche
N8N_TOPIC_WEBHOOK_URL=http://localhost:5678/webhook/topic
N8N_POST_WEBHOOK_URL=http://localhost:5678/webhook/post

# Admin Configuration
ADMIN_CHAT_ID=your_admin_chat_id_here
ENABLE_ADMIN_NOTIFICATIONS=True

# Bot Configuration
MAX_USERS=1000
DEBUG=True
```

### 4. Запустить бота
```bash
# Запуск с новой конфигурацией
docker-compose up -d

# Проверить логи
docker logs innokentiy-bot -f
```

## ✅ Преимущества .env

- ✅ Docker Compose автоматически читает .env
- ✅ Стандартный формат, поддерживаемый всеми инструментами
- ✅ Переменные ${VAR} работают из коробки
- ✅ Проще отладка
- ✅ Меньше конфигурации

## 🔍 Проверка

```bash
# Проверить, что переменные загружены
docker-compose config | grep -A 5 environment

# Проверить переменные в контейнере
docker exec innokentiy-bot env | grep -E "(TELEGRAM|SUPABASE)"
```

## 🗑️ Очистка старых файлов

После успешного запуска можно удалить:
```bash
rm config.env
rm config.env.example  
rm config.env.server-example
```
