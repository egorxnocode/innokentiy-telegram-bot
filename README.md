# 🤖 Innokentiy Telegram Bot

Продвинутый Telegram бот для генерации постов с интеграцией N8N и OpenAI.

## ✨ Возможности

### 🔐 Система регистрации
- **Email валидация** через Supabase
- **Определение ниши** через N8N + AI
- **Голосовые сообщения** с транскрибацией OpenAI

### 📝 Генерация постов
- **Ежедневные напоминания** в 9:00
- **Адаптация тем** под нишу пользователя
- **Генерация контента** на основе ответов
- **Еженедельный лимит** 10 постов
- **Поддержка голосовых ответов**

### 🔧 Администрирование
- **Автоматические уведомления** об ошибках
- **Мониторинг таймаутов** N8N
- **Детальная информация** о пользователях
- **Система здоровья** с health checks

### 🛠️ Техническая база
- **Docker контейнеризация**
- **Supabase база данных** с RLS
- **N8N интеграция** (3 специализированных вебхука)
- **OpenAI Whisper** для транскрибации
- **Graceful shutdown** и error handling

## 🚀 Быстрый старт

### 1. Клонирование репозитория
```bash
git clone https://github.com/username/innokentiy-bot.git
cd innokentiy-bot
```

### 2. Настройка
```bash
# Автоматическая настройка
./setup.sh

# Или ручная настройка
cp config.env.example config.env
nano config.env
```

### 3. Запуск
```bash
# Развертывание
./scripts/deploy.sh

# Проверка статуса
./scripts/status.sh
```

## ⚙️ Конфигурация

### Обязательные переменные в `config.env`:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=1234567890:AAEhBOwwepo6LRDLuHOPEXAMPLE

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# OpenAI
OPENAI_API_KEY=sk-...

# N8N Webhooks
N8N_NICHE_WEBHOOK_URL=https://your-n8n.com/webhook/niche-detection
N8N_TOPIC_WEBHOOK_URL=https://your-n8n.com/webhook/topic-adaptation
N8N_POST_WEBHOOK_URL=https://your-n8n.com/webhook/post-generation

# Admin Notifications
ADMIN_CHAT_ID=123456789
ENABLE_ADMIN_NOTIFICATIONS=True
```

## 🏗️ Архитектура

### Контейнеры
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram Bot  │    │      N8N        │    │    Supabase     │
│   (этот проект) │◄──►│   (внешний)     │    │   (внешний)     │
│                 │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### База данных
- `users` - пользователи и их состояния
- `daily_content` - ежедневный контент (сообщения + темы + вопросы)
- `user_post_limits` - еженедельные лимиты
- `generated_posts` - история постов

### N8N Workflows
1. **Niche Detection** - определение ниши по описанию
2. **Topic Adaptation** - адаптация темы под нишу
3. **Post Generation** - генерация поста по ответу

## 🛠️ Команды управления

```bash
# Развертывание
./scripts/deploy.sh              # Полное развертывание
./scripts/deploy.sh staging      # Развертывание в staging

# Мониторинг
./scripts/status.sh              # Полный статус системы
./scripts/logs.sh follow         # Логи в реальном времени
./scripts/logs.sh errors         # Только ошибки

# Управление
./scripts/restart.sh soft        # Быстрый перезапуск
./scripts/restart.sh hard        # Пересборка образа
./scripts/stop.sh                # Остановка
./scripts/stop.sh clean          # Полная очистка

# Резервное копирование
./scripts/backup.sh              # Создание бэкапа
```

## 📊 Мониторинг

### Health Check
```bash
curl http://localhost:8080/health
```

### Логи
```bash
# Просмотр логов
./scripts/logs.sh follow

# Только ошибки
./scripts/logs.sh errors

# Статистика
./scripts/logs.sh stats
```

### Админские уведомления
Автоматические уведомления в Telegram о:
- 🔴 Ошибках пользователей
- 🟡 Таймаутах N8N
- 🚨 Критических проблемах

## 🔧 Разработка

### Локальный запуск
```bash
# Установка зависимостей
pip install -r requirements.txt

# Настройка переменных
cp config.env.example config.env

# Запуск
python main.py
```

### Структура проекта
```
├── main.py                 # Точка входа
├── bot.py                  # Telegram bot логика
├── database.py             # Работа с Supabase
├── post_system.py          # Система генерации постов
├── admin_notifier.py       # Админские уведомления
├── scheduler.py            # Планировщик напоминаний
├── utils.py                # Утилиты
├── error_handler.py        # Обработка ошибок
├── messages.py             # Тексты сообщений
├── config.py               # Конфигурация
├── Dockerfile              # Docker образ
├── docker-compose.yml      # Docker Compose
└── scripts/                # Скрипты управления
    ├── deploy.sh
    ├── logs.sh
    ├── restart.sh
    ├── stop.sh
    ├── status.sh
    └── backup.sh
```

## 🐳 Docker

### Сборка образа
```bash
docker-compose build
```

### Запуск
```bash
docker-compose up -d
```

### Подключение к внешним сервисам
Бот подключается к внешней сети `services-network` для связи с N8N и Supabase.

## 📈 Производительность

### Ресурсы
- **Память**: 256MB - 512MB
- **CPU**: 0.25 - 0.5 cores
- **Диск**: ~100MB (без логов)

### Масштабирование
- Поддержка до 1000 пользователей
- Еженедельный лимит 10 постов на пользователя
- Автоматическая очистка старых логов

## 🔒 Безопасность

### Контейнеризация
- Непривилегированный пользователь
- Минимальный базовый образ
- Изолированная сеть

### Данные
- Переменные окружения для секретов
- RLS политики в Supabase
- Ограниченные права доступа

## 🐛 Отладка

### Проблемы с запуском
```bash
# Проверка статуса
./scripts/status.sh

# Просмотр логов
./scripts/logs.sh errors

# Жесткий перезапуск
./scripts/restart.sh hard
```

### Проблемы с N8N
```bash
# Проверка конфигурации вебхуков
grep N8N config.env

# Тест подключения
curl -X POST $N8N_NICHE_WEBHOOK_URL -H "Content-Type: application/json" -d '{"test":true}'
```

### Проблемы с Supabase
```bash
# Проверка подключения
curl "$SUPABASE_URL/rest/v1/" -H "apikey: $SUPABASE_KEY"
```

## 📚 Документация

- [N8N Webhook Guide](N8N_WEBHOOK_GUIDE.md) - Настройка N8N workflows
- [Admin Notifications Guide](ADMIN_NOTIFICATIONS_GUIDE.md) - Админские уведомления
- [Database Schema](database_schema.sql) - Схема базы данных

## 🤝 Вклад в проект

1. Fork репозитория
2. Создайте feature branch
3. Внесите изменения
4. Добавьте тесты
5. Создайте Pull Request

## 📄 Лицензия

MIT License - см. [LICENSE](LICENSE) файл.

## 📞 Поддержка

- **Issues**: [GitHub Issues](https://github.com/username/innokentiy-bot/issues)
- **Документация**: [Wiki](https://github.com/username/innokentiy-bot/wiki)
- **Обсуждения**: [Discussions](https://github.com/username/innokentiy-bot/discussions)

---

Made with ❤️ for content creators