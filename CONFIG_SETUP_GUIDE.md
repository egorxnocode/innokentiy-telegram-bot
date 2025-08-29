# 🔧 Гайд по настройке config.env

Это пошаговая инструкция по заполнению файла `config.env` на сервере с существующими N8N и Supabase.

## 🚀 Быстрый старт

```bash
# На сервере
cd /opt/innokentiy-telegram-bot
cp config.env.server-example config.env
nano config.env
```

## 📋 Пошаговое заполнение

### 1. 🤖 Telegram Bot Token

```env
TELEGRAM_BOT_TOKEN=1234567890:ABCDEFghijklmnopqrstuvwxyz123456789
```

**Как получить:**
1. Найдите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте `/newbot` (если бот еще не создан) или `/mybots`
3. Скопируйте токен вида `1234567890:ABCDEFghijklmnopqrstuvwxyz123456789`

### 2. 🗄️ Supabase Configuration

#### 2.1 Проверка доступности Supabase

```bash
# На сервере проверьте, что Supabase работает
curl http://localhost:8000/health
```

#### 2.2 Получение Supabase ключей

**Вариант A: Через веб-интерфейс**
1. Откройте http://localhost:8000 (или IP_сервера:8000)
2. Войдите в Dashboard
3. Перейдите в Settings → API
4. Скопируйте:
   - `Project URL` → `SUPABASE_URL`
   - `anon public` key → `SUPABASE_KEY`

**Вариант B: Через Docker логи**
```bash
# Найдите ключи в логах Supabase
docker logs supabase-kong 2>&1 | grep -i "key\|token"
```

**Заполнение:**
```env
SUPABASE_URL=http://localhost:8000
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6...
```

### 3. 🔗 N8N Webhook Configuration

#### 3.1 Доступ к N8N

```bash
# Проверка доступности N8N
curl http://localhost:5678
```

#### 3.2 Настройка N8N Workflows

1. **Откройте N8N:** http://localhost:5678 (или IP_сервера:5678)

2. **Войдите в систему:**
   - Логин: `admin` (или из ваших настроек)
   - Пароль: смотрите в логах N8N или ваших записях

3. **Создайте 3 Workflow:**

#### Workflow 1: Определение ниши
1. Создайте новый Workflow
2. Добавьте узел **Webhook**
3. Настройте путь: `niche`
4. Активируйте Workflow
5. Скопируйте Webhook URL: `http://localhost:5678/webhook/niche`

#### Workflow 2: Адаптация темы
1. Создайте новый Workflow  
2. Добавьте узел **Webhook**
3. Настройте путь: `topic`
4. Активируйте Workflow
5. Скопируйте Webhook URL: `http://localhost:5678/webhook/topic`

#### Workflow 3: Генерация поста
1. Создайте новый Workflow
2. Добавьте узел **Webhook** 
3. Настройте путь: `post`
4. Активируйте Workflow
5. Скопируйте Webhook URL: `http://localhost:5678/webhook/post`

**Заполнение в config.env:**
```env
N8N_NICHE_WEBHOOK_URL=http://localhost:5678/webhook/niche
N8N_TOPIC_WEBHOOK_URL=http://localhost:5678/webhook/topic  
N8N_POST_WEBHOOK_URL=http://localhost:5678/webhook/post
```

### 4. 🧠 OpenAI API Key

```env
OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz1234567890
```

**Как получить:**
1. Зайдите на https://platform.openai.com/api-keys
2. Войдите в аккаунт
3. Создайте новый API ключ
4. Скопируйте ключ (начинается с `sk-`)

### 5. 👨‍💼 Admin Chat ID

```env
ADMIN_CHAT_ID=123456789
```

**Как получить:**
1. Найдите [@userinfobot](https://t.me/userinfobot) в Telegram
2. Отправьте ему любое сообщение  
3. Скопируйте ваш `Chat ID` (число)

## 📝 Итоговый config.env

Примерный заполненный файл:

```env
# Telegram Bot
TELEGRAM_BOT_TOKEN=1234567890:ABCDEFghijklmnopqrstuvwxyz123456789

# Supabase  
SUPABASE_URL=http://localhost:8000
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSI...

# N8N Webhooks
N8N_NICHE_WEBHOOK_URL=http://localhost:5678/webhook/niche
N8N_TOPIC_WEBHOOK_URL=http://localhost:5678/webhook/topic
N8N_POST_WEBHOOK_URL=http://localhost:5678/webhook/post

# OpenAI
OPENAI_API_KEY=sk-proj-abcdefghijklmnopqrstuvwxyz1234567890

# Admin
ADMIN_CHAT_ID=123456789
ENABLE_ADMIN_NOTIFICATIONS=True

# Bot Config
MAX_USERS=1000
DEBUG=True
```

## 🔍 Проверка конфигурации

После заполнения config.env:

```bash
# Проверить, что все переменные заполнены
grep -E "^[A-Z_]+=" config.env | grep -v "your_.*_here"

# Запустить бота
docker-compose up -d

# Проверить логи
docker logs innokentiy-bot -f
```

## ❗ Частые проблемы

### Проблема: Supabase ключ не найден
**Решение:** Проверьте логи Supabase:
```bash
docker logs supabase-kong | grep -i "jwt\|key"
```

### Проблема: N8N требует авторизацию
**Решение:** Найдите логин/пароль в логах:
```bash
docker logs n8n-n8n-1 | grep -i "user\|password\|login"
```

### Проблема: Webhook не работает
**Решение:** 
1. Убедитесь, что Workflow активирован в N8N
2. Проверьте правильность пути webhook'а
3. Тестируйте webhook через curl:
```bash
curl -X POST http://localhost:5678/webhook/niche \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

## 🔒 Безопасность

- ❌ Не публикуйте config.env в git
- ✅ Используйте сильные пароли
- ✅ Ограничьте доступ к серверу
- ✅ Регулярно обновляйте ключи API
