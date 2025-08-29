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

-- 5. Удаляем старые таблицы и функции (осторожно!)
-- Раскомментируйте следующие строки только после проверки миграции данных:

-- DROP TABLE IF EXISTS user_post_limits CASCADE;
-- DROP TABLE IF EXISTS generated_posts CASCADE;
-- DROP FUNCTION IF EXISTS check_user_post_limit(BIGINT);
-- DROP FUNCTION IF EXISTS increment_user_post_count(BIGINT);
-- DROP FUNCTION IF EXISTS get_week_start();

COMMIT;

-- ПРОВЕРКА МИГРАЦИИ:
-- SELECT COUNT(*) as old_posts FROM generated_posts;
-- SELECT COUNT(*) as new_posts FROM user_posts;
-- SELECT * FROM user_posts ORDER BY created_at DESC LIMIT 5;
