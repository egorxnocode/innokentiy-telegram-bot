# ПОШАГОВАЯ МИГРАЦИЯ НА СЕРВЕРЕ

## 🔥 КРИТИЧЕСКИ ВАЖНО! Выполнить в указанном порядке:

### 1. Обновить код на сервере
```bash
cd /opt/innokentiy-telegram-bot
git pull origin main
```

### 2. Выполнить миграции в Supabase Dashboard

#### ШАГ 1: Основная миграция (migration_simple_counter.sql)
Зайти в **Supabase Dashboard → SQL Editor** и выполнить:

```sql
-- МИГРАЦИЯ НА ПРОСТУЮ СИСТЕМУ СЧЕТЧИКА ПОСТОВ
-- Этот файл нужно выполнить на сервере для обновления базы данных

BEGIN;

-- 1. Создаем новую простую таблицу
CREATE TABLE IF NOT EXISTS user_posts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_content TEXT NOT NULL,
    adapted_topic TEXT,
    user_question TEXT,
    user_answer TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- 2. Создаем индексы
CREATE INDEX IF NOT EXISTS idx_user_posts_user_id ON user_posts(user_id);
CREATE INDEX IF NOT EXISTS idx_user_posts_created_at ON user_posts(created_at);
CREATE INDEX IF NOT EXISTS idx_user_posts_user_created ON user_posts(user_id, created_at);

-- 3. Настраиваем политики безопасности
ALTER TABLE user_posts ENABLE ROW LEVEL SECURITY;
CREATE POLICY "Enable all access for service role" ON user_posts FOR ALL USING (true);

-- 4. Мигрируем данные из старой таблицы generated_posts (если есть)
INSERT INTO user_posts (user_id, post_content, adapted_topic, user_question, user_answer, created_at)
SELECT 
    user_id,
    COALESCE(generated_content, 'Мигрированный пост') as post_content,
    COALESCE(adapted_topic, '') as adapted_topic,
    COALESCE(user_question, '') as user_question,
    COALESCE(user_answer, '') as user_answer,
    created_at
FROM generated_posts
WHERE generated_posts.id IS NOT NULL
ON CONFLICT DO NOTHING;

COMMIT;
```

#### ШАГ 2: Добавление счетчика (add_weekly_counter.sql)
После успешного выполнения первой миграции, выполнить:

```sql
-- ДОБАВЛЕНИЕ ПРОСТОГО ЕЖЕНЕДЕЛЬНОГО СЧЕТЧИКА К ПОЛЬЗОВАТЕЛЯМ

BEGIN;

-- 1. Добавляем поле счетчика постов к таблице users
ALTER TABLE users ADD COLUMN IF NOT EXISTS weekly_posts_count INTEGER DEFAULT 0 NOT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_week_reset DATE DEFAULT CURRENT_DATE;

-- 2. Создаем функцию для обнуления счетчика в понедельник
CREATE OR REPLACE FUNCTION reset_weekly_counters()
RETURNS INTEGER AS $$
DECLARE
    current_monday DATE;
    updated_count INTEGER;
BEGIN
    -- Получаем дату текущего понедельника
    current_monday := CURRENT_DATE - (EXTRACT(DOW FROM CURRENT_DATE)::INTEGER - 1);
    
    -- Обнуляем счетчики для пользователей, у которых last_week_reset < текущий понедельник
    UPDATE users 
    SET weekly_posts_count = 0,
        last_week_reset = current_monday
    WHERE last_week_reset < current_monday;
    
    GET DIAGNOSTICS updated_count = ROW_COUNT;
    
    RETURN updated_count;
END;
$$ LANGUAGE plpgsql;

-- 3. Создаем функцию для увеличения счетчика поста
CREATE OR REPLACE FUNCTION increment_weekly_post_counter(p_user_id BIGINT)
RETURNS INTEGER AS $$
DECLARE
    current_monday DATE;
    new_count INTEGER;
BEGIN
    current_monday := CURRENT_DATE - (EXTRACT(DOW FROM CURRENT_DATE)::INTEGER - 1);
    
    -- Сначала обновляем счетчик недели если нужно
    UPDATE users 
    SET weekly_posts_count = 0,
        last_week_reset = current_monday
    WHERE id = p_user_id AND last_week_reset < current_monday;
    
    -- Увеличиваем счетчик постов
    UPDATE users 
    SET weekly_posts_count = weekly_posts_count + 1
    WHERE id = p_user_id
    RETURNING weekly_posts_count INTO new_count;
    
    RETURN COALESCE(new_count, 0);
END;
$$ LANGUAGE plpgsql;

-- 4. Заполняем текущие значения счетчика для существующих пользователей
UPDATE users 
SET weekly_posts_count = (
    SELECT COUNT(*)
    FROM user_posts up
    WHERE up.user_id = users.id 
    AND up.created_at >= (CURRENT_DATE - INTERVAL '7 days')
),
last_week_reset = CURRENT_DATE - (EXTRACT(DOW FROM CURRENT_DATE)::INTEGER - 1)
WHERE EXISTS (
    SELECT 1 FROM user_posts up WHERE up.user_id = users.id
);

COMMIT;
```

### 3. Активировать новую систему в коде

После успешного выполнения **ОБЕИХ** миграций, нужно убрать временные заглушки из кода:

В файле `database.py` заменить временный код на использование новых SQL функций.

### 4. Перезапустить бот
```bash
docker-compose up -d --build --force-recreate telegram-bot
```

### 5. Проверить работу
- Кнопка "👤 Профиль" должна показывать правильную информацию
- Счетчик постов должен работать корректно
- Никаких ошибок в логах

## ⚠️ ВАЖНО:
- Выполнять миграции **строго по порядку**
- Проверять успешность каждого шага
- При ошибках - остановиться и не продолжать

## 🔍 Проверка результата:
```sql
-- Проверить таблицу user_posts
SELECT COUNT(*) FROM user_posts;

-- Проверить новые поля в users
SELECT id, email, weekly_posts_count, last_week_reset FROM users LIMIT 5;

-- Проверить функции
SELECT reset_weekly_counters();
```
