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
-- Считаем посты за последние 7 дней для каждого пользователя
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

-- КОММЕНТАРИИ
COMMENT ON COLUMN users.weekly_posts_count IS 'Количество постов за текущую неделю (обнуляется в понедельник)';
COMMENT ON COLUMN users.last_week_reset IS 'Дата последнего обнуления счетчика (понедельник)';
COMMENT ON FUNCTION reset_weekly_counters() IS 'Обнуляет счетчики постов для всех пользователей в понедельник';
COMMENT ON FUNCTION increment_weekly_post_counter(BIGINT) IS 'Увеличивает счетчик постов пользователя на 1';

-- ПРОВЕРКА
-- SELECT id, email, weekly_posts_count, last_week_reset FROM users LIMIT 5;
