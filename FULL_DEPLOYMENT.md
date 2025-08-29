# Полное развертывание: Bot + Supabase + N8N

Этот гайд показывает, как развернуть весь стек (Telegram Bot, Supabase, N8N) в единой Docker сети.

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network                          │
│                   innokentiy-network                       │
│                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   PostgreSQL │  │   Supabase   │  │     N8N      │     │
│  │   postgres   │  │   supabase   │  │     n8n      │     │
│  │   :5432      │  │   :8000      │  │   :5678      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                           │                  │             │
│                    ┌──────────────┐          │             │
│                    │ Telegram Bot │──────────┘             │
│                    │ innokentiy-  │                        │
│                    │    bot       │                        │
│                    └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

## Преимущества

- ✅ Все сервисы в одной сети
- ✅ Обращение по именам контейнеров
- ✅ Изолированная среда
- ✅ Простое масштабирование
- ✅ Единый docker-compose файл

## Развертывание

### 1. Подготовка конфигурации

```bash
# Копируем пример конфигурации
cp config.env.example config.env

# Редактируем конфигурацию
nano config.env
```

### 2. Заполните обязательные поля в config.env:

```env
# Telegram Bot Token (получить у @BotFather)
TELEGRAM_BOT_TOKEN=your_actual_bot_token

# OpenAI API Key для транскрипции голосовых сообщений
OPENAI_API_KEY=your_openai_key

# Админский чат для уведомлений
ADMIN_CHAT_ID=your_telegram_chat_id

# Пароль для PostgreSQL (можно оставить по умолчанию)
POSTGRES_PASSWORD=supabase123

# N8N логин/пароль для веб-интерфейса
N8N_USER=admin
N8N_PASSWORD=secure_password_here

# Supabase ключи (сгенерируются автоматически или настроить вручную)
JWT_SECRET=your-super-secret-jwt-token-with-at-least-32-characters-long
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_KEY=your_supabase_service_key
```

### 3. Запуск всего стека

```bash
# Использовать полную конфигурацию
docker-compose -f docker-compose.full.yml up -d

# Или создать симлинк для удобства
ln -sf docker-compose.full.yml docker-compose.yml
docker-compose up -d
```

### 4. Проверка запуска

```bash
# Статус всех контейнеров
docker-compose ps

# Логи всех сервисов
docker-compose logs

# Логи конкретного сервиса
docker-compose logs telegram-bot
docker-compose logs supabase
docker-compose logs n8n
```

## Доступ к сервисам

После запуска сервисы будут доступны:

### Внешний доступ (с хост-машины):
- **Supabase Dashboard**: http://localhost:8000
- **N8N Interface**: http://localhost:5678
- **PostgreSQL**: localhost:5432

### Внутренний доступ (между контейнерами):
- **Supabase**: http://supabase:8000
- **N8N Webhooks**: http://n8n:5678/webhook/*
- **PostgreSQL**: postgres:5432

## Настройка N8N Workflows

1. Откройте http://localhost:5678
2. Войдите используя N8N_USER и N8N_PASSWORD
3. Создайте workflows для:
   - `/webhook/niche` - определение ниши
   - `/webhook/topic` - адаптация темы
   - `/webhook/post` - генерация поста

## Настройка Supabase

1. Откройте http://localhost:8000
2. Supabase автоматически создаст таблицы из database_schema.sql
3. Настройте RLS (Row Level Security) при необходимости

## Мониторинг

```bash
# Использование ресурсов
docker stats

# Логи в реальном времени
docker-compose logs -f

# Статус health check
curl http://localhost:8080/health
```

## Остановка и обслуживание

```bash
# Остановка всех сервисов
docker-compose down

# Остановка с удалением volumes (ОСТОРОЖНО!)
docker-compose down -v

# Обновление образов
docker-compose pull
docker-compose up -d

# Перезапуск отдельного сервиса
docker-compose restart telegram-bot
```

## Резервное копирование

```bash
# Бэкап PostgreSQL
docker exec postgres-db pg_dump -U supabase supabase > backup.sql

# Бэкап N8N workflows
docker cp n8n-server:/home/node/.n8n ./n8n-backup
```

## Troubleshooting

### Проблемы с подключением между контейнерами

```bash
# Проверка сети
docker network ls
docker network inspect innokentiy-network

# Тест связности между контейнерами
docker exec innokentiy-bot ping supabase
docker exec innokentiy-bot ping n8n
```

### Проблемы с базой данных

```bash
# Подключение к PostgreSQL
docker exec -it postgres-db psql -U supabase

# Проверка таблиц
\dt

# Просмотр логов PostgreSQL
docker-compose logs postgres
```

### Проблемы с Supabase

```bash
# Логи Supabase
docker-compose logs supabase

# Перезапуск Supabase
docker-compose restart supabase
```

## Обновление

1. Обновите код из git
2. Пересоберите образ бота:
   ```bash
   docker-compose build telegram-bot
   docker-compose up -d telegram-bot
   ```

## Безопасность

- ✅ Все сервисы изолированы в Docker сети
- ✅ PostgreSQL не доступен извне (только через Supabase)
- ✅ N8N защищен базовой аутентификацией
- ✅ Все пароли в config.env (не в git)
- ⚠️ Измените пароли по умолчанию в продакшене
- ⚠️ Настройте HTTPS для внешнего доступа
