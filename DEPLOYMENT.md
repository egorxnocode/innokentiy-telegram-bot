# 🚀 Руководство по развертыванию

## 📋 Предварительные требования

### На сервере должны быть развернуты:

1. **N8N контейнер** с тремя настроенными workflows
2. **Supabase контейнер** с настроенной базой данных
3. **Docker и Docker Compose** для развертывания бота

### Системные требования:
- **CPU**: 1+ cores
- **RAM**: 1GB+
- **Диск**: 2GB свободного места
- **OS**: Linux (Ubuntu 20.04+ рекомендуется)

## 🌐 Подготовка серверной инфраструктуры

### 1. Создание Docker сети
```bash
# Создайте общую сеть для всех сервисов
docker network create services-network
```

### 2. N8N контейнер
```bash
# Если N8N еще не развернут
docker run -d \
  --name n8n \
  --network services-network \
  -p 5678:5678 \
  -v n8n_data:/home/node/.n8n \
  n8nio/n8n

# Настройте 3 workflow в N8N:
# 1. niche-detection - определение ниши
# 2. topic-adaptation - адаптация темы  
# 3. post-generation - генерация поста
```

### 3. Supabase контейнер
```bash
# Если Supabase еще не развернут
git clone https://github.com/supabase/supabase
cd supabase/docker
docker-compose up -d

# Подключите Supabase к общей сети
docker network connect services-network supabase_db_1
docker network connect services-network supabase_rest_1
```

## 📦 Развертывание бота

### 1. Клонирование репозитория
```bash
# На сервере
git clone https://github.com/username/innokentiy-bot.git
cd innokentiy-bot
```

### 2. Автоматическая настройка
```bash
# Запустить интерактивную настройку
./setup.sh
```

### 3. Ручная настройка (альтернатива)
```bash
# Копировать конфигурацию
cp config.env.example config.env

# Отредактировать переменные
nano config.env
```

### 4. Заполнение config.env
```env
# === ОБЯЗАТЕЛЬНЫЕ ПЕРЕМЕННЫЕ ===

# Telegram Bot Token (от @BotFather)
TELEGRAM_BOT_TOKEN=1234567890:AAEhBOwwepo6LRDLuHOPEXAMPLE

# Supabase (внешний контейнер)
SUPABASE_URL=http://supabase_rest_1:3000
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# OpenAI для транскрибации
OPENAI_API_KEY=sk-...

# N8N Webhooks (внешний контейнер)
N8N_NICHE_WEBHOOK_URL=http://n8n:5678/webhook/niche-detection
N8N_TOPIC_WEBHOOK_URL=http://n8n:5678/webhook/topic-adaptation
N8N_POST_WEBHOOK_URL=http://n8n:5678/webhook/post-generation

# Admin уведомления
ADMIN_CHAT_ID=123456789
ENABLE_ADMIN_NOTIFICATIONS=True

# === ОПЦИОНАЛЬНЫЕ ПЕРЕМЕННЫЕ ===
MAX_USERS=1000
DEBUG=False
```

### 5. Развертывание
```bash
# Полное развертывание
./scripts/deploy.sh

# Проверка статуса
./scripts/status.sh
```

## 🔧 Настройка N8N Workflows

### 1. Niche Detection Workflow
```javascript
// HTTP Request Node - Webhook
// Method: POST
// Path: /webhook/niche-detection

// OpenAI Node
// Operation: Complete
// Model: gpt-3.5-turbo
// Prompt: 
"Определи профессиональную нишу по описанию: {{$json.description}}"

// Response Node
{
  "niche": "{{$json.choices[0].message.content}}"
}
```

### 2. Topic Adaptation Workflow
```javascript
// HTTP Request Node - Webhook
// Method: POST
// Path: /webhook/topic-adaptation

// OpenAI Node
// Prompt:
"Адаптируй тему '{{$json.topic}}' под нишу '{{$json.niche}}'"

// Response Node
{
  "adapted_topic": "{{$json.choices[0].message.content}}"
}
```

### 3. Post Generation Workflow
```javascript
// HTTP Request Node - Webhook
// Method: POST
// Path: /webhook/post-generation

// OpenAI Node
// Prompt:
"Создай пост для соцсетей:
Ниша: {{$json.niche}}
Тема: {{$json.topic}}
Ответ: {{$json.user_answer}}"

// Response Node
{
  "generated_post": "{{$json.choices[0].message.content}}"
}
```

## 🗄️ Настройка Supabase

### 1. Создание таблиц
```bash
# Выполните SQL схему
psql -h localhost -U postgres -d postgres -f database_schema.sql
```

### 2. Настройка RLS политик
```sql
-- Выполните в Supabase SQL Editor
-- Политики уже включены в database_schema.sql
```

### 3. Добавление email адресов
```sql
-- Добавьте разрешенные email для регистрации
INSERT INTO allowed_emails (email) VALUES 
('user1@example.com'),
('user2@example.com');
```

## 🔍 Проверка развертывания

### 1. Проверка контейнеров
```bash
# Статус всех контейнеров
docker ps

# Логи бота
./scripts/logs.sh follow
```

### 2. Проверка подключений
```bash
# Health check бота
curl http://localhost:8080/health

# Тест N8N
curl -X POST http://localhost:5678/webhook/niche-detection \
  -H "Content-Type: application/json" \
  -d '{"description": "я программист"}'

# Тест Supabase
curl http://localhost:3000/rest/v1/users \
  -H "apikey: YOUR_SUPABASE_KEY"
```

### 3. Тест Telegram бота
```
1. Найдите бота в Telegram
2. Отправьте /start
3. Проверьте регистрацию
4. Проверьте генерацию постов
```

## 🔧 Управление в продакшене

### Ежедневные команды
```bash
# Проверка статуса
./scripts/status.sh

# Просмотр логов
./scripts/logs.sh tail 50

# Проверка ошибок
./scripts/logs.sh errors
```

### Обновление
```bash
# Получить новую версию
git pull origin main

# Жесткий перезапуск с пересборкой
./scripts/restart.sh hard
```

### Резервное копирование
```bash
# Создание бэкапа
./scripts/backup.sh

# Бэкапы сохраняются в backups/
ls -la backups/
```

## 🚨 Мониторинг и алерты

### Автоматические уведомления
Бот автоматически отправляет уведомления в админский чат о:
- ❌ Ошибках пользователей
- ⏰ Таймаутах N8N
- 🚨 Критических проблемах

### Логи
```bash
# Логи в реальном времени
./scripts/logs.sh follow

# Только ошибки
./scripts/logs.sh errors

# Статистика логов
./scripts/logs.sh stats
```

### Health Check
```bash
# Ручная проверка
curl http://localhost:8080/health

# Автоматическая через cron
echo "*/5 * * * * curl -f http://localhost:8080/health || echo 'Bot down'" | crontab -
```

## 🔄 Восстановление после сбоев

### 1. Бот не отвечает
```bash
# Проверка статуса
./scripts/status.sh

# Мягкий перезапуск
./scripts/restart.sh soft

# Если не помогает - жесткий
./scripts/restart.sh hard
```

### 2. Ошибки N8N
```bash
# Проверка N8N
docker logs n8n

# Перезапуск N8N
docker restart n8n

# Тест вебхуков
curl -X POST http://n8n:5678/webhook/test
```

### 3. Проблемы с Supabase
```bash
# Проверка Supabase
docker logs supabase_rest_1

# Перезапуск
docker restart supabase_rest_1 supabase_db_1
```

### 4. Полное восстановление
```bash
# Остановка всех сервисов
./scripts/stop.sh clean

# Восстановление из бэкапа
tar -xzf backups/innokentiy_bot_backup_YYYYMMDD_HHMMSS.tar.gz
docker load < docker_image.tar

# Перезапуск
./scripts/deploy.sh
```

## 📊 Производительность

### Рекомендуемые ресурсы
```yaml
# docker-compose.yml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
    reservations:
      memory: 256M
      cpus: '0.25'
```

### Масштабирование
- **До 1000 пользователей**: текущая конфигурация
- **1000+ пользователей**: увеличьте лимиты ресурсов
- **Высокая нагрузка**: добавьте load balancer

## 🔒 Безопасность

### Обновления
```bash
# Регулярно обновляйте образы
docker-compose pull
./scripts/restart.sh hard
```

### Логи
```bash
# Очистка старых логов (автоматически в скриптах)
./scripts/logs.sh clear
```

### Секреты
- Никогда не коммитьте `config.env`
- Используйте strong passwords
- Регулярно ротируйте API ключи

## 📞 Поддержка

### Логи для отладки
```bash
# Собрать диагностическую информацию
./scripts/status.sh > debug_info.txt
./scripts/logs.sh errors >> debug_info.txt
docker ps >> debug_info.txt
```

### Частые проблемы

**Бот не отвечает на сообщения:**
- Проверьте TELEGRAM_BOT_TOKEN
- Убедитесь что webhook не настроен для бота

**N8N таймауты:**
- Увеличьте таймауты в config.py
- Оптимизируйте N8N workflows
- Проверьте OpenAI API лимиты

**Supabase ошибки:**
- Проверьте RLS политики
- Убедитесь в правильности SUPABASE_KEY
- Проверьте сетевое подключение

---

🎉 **Развертывание завершено!** Ваш бот готов к работе.
