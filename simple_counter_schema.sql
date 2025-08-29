-- НОВАЯ ПРОСТАЯ СИСТЕМА СЧЕТЧИКА ПОСТОВ
-- Заменяет сложные таблицы user_post_limits и generated_posts

-- Удаляем старые таблицы и функции
DROP TABLE IF EXISTS user_post_limits CASCADE;
DROP TABLE IF EXISTS generated_posts CASCADE;
DROP FUNCTION IF EXISTS check_user_post_limit(BIGINT);
DROP FUNCTION IF EXISTS increment_user_post_count(BIGINT);
DROP FUNCTION IF EXISTS get_week_start();

-- Простая таблица для постов пользователей
CREATE TABLE IF NOT EXISTS user_posts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    post_content TEXT NOT NULL,
    adapted_topic TEXT,
    user_question TEXT,
    user_answer TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Индексы для быстрых запросов
CREATE INDEX IF NOT EXISTS idx_user_posts_user_id ON user_posts(user_id);
CREATE INDEX IF NOT EXISTS idx_user_posts_created_at ON user_posts(created_at);
CREATE INDEX IF NOT EXISTS idx_user_posts_user_created ON user_posts(user_id, created_at);

-- Комментарии
COMMENT ON TABLE user_posts IS 'Простая таблица для хранения всех постов пользователей';
COMMENT ON COLUMN user_posts.user_id IS 'ID пользователя из таблицы users';
COMMENT ON COLUMN user_posts.post_content IS 'Сгенерированный контент поста';
COMMENT ON COLUMN user_posts.adapted_topic IS 'Адаптированная тема поста';
COMMENT ON COLUMN user_posts.user_question IS 'Вопрос, заданный пользователю';
COMMENT ON COLUMN user_posts.user_answer IS 'Ответ пользователя на вопрос';
COMMENT ON COLUMN user_posts.created_at IS 'Дата и время создания поста';
