-- Схема базы данных для Telegram бота
-- Используйте этот SQL в Supabase SQL Editor

-- Таблица разрешенных email адресов
CREATE TABLE IF NOT EXISTS allowed_emails (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL
);

-- Индекс для быстрого поиска по email
CREATE INDEX IF NOT EXISTS idx_allowed_emails_email ON allowed_emails(email);

-- Таблица пользователей
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    niche TEXT,
    state VARCHAR(50) DEFAULT 'waiting_email' NOT NULL,
    registration_date TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    subscription_status VARCHAR(50) DEFAULT 'inactive',
    subscription_end_date TIMESTAMP WITH TIME ZONE,
    reminder_enabled BOOLEAN DEFAULT true NOT NULL,
    reminder_time TIME DEFAULT '09:00:00',
    timezone VARCHAR(50) DEFAULT 'Europe/Moscow'
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_state ON users(state);
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);
CREATE INDEX IF NOT EXISTS idx_users_subscription_status ON users(subscription_status);

-- Таблица для логирования действий пользователей (опционально)
CREATE TABLE IF NOT EXISTS user_actions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action_type VARCHAR(100) NOT NULL,
    action_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Индекс для логов
CREATE INDEX IF NOT EXISTS idx_user_actions_user_id ON user_actions(user_id);
CREATE INDEX IF NOT EXISTS idx_user_actions_created_at ON user_actions(created_at);
CREATE INDEX IF NOT EXISTS idx_user_actions_type ON user_actions(action_type);

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = TIMEZONE('utc'::text, NOW());
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для автоматического обновления updated_at в таблице users
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Добавление политик Row Level Security (RLS) для безопасности
ALTER TABLE allowed_emails ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_actions ENABLE ROW LEVEL SECURITY;

-- Политики для allowed_emails (только чтение для сервиса)
CREATE POLICY "Enable read access for service role" ON allowed_emails
    FOR SELECT USING (true);

-- Политики для users (полный доступ для сервиса)
CREATE POLICY "Enable all access for service role" ON users
    FOR ALL USING (true);

-- Политики для user_actions (полный доступ для сервиса)
CREATE POLICY "Enable all access for service role" ON user_actions
    FOR ALL USING (true);

-- Функция для получения статистики
CREATE OR REPLACE FUNCTION get_bot_statistics()
RETURNS TABLE (
    total_users BIGINT,
    active_users BIGINT,
    registered_users BIGINT,
    users_today BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        COUNT(*) as total_users,
        COUNT(*) FILTER (WHERE is_active = true) as active_users,
        COUNT(*) FILTER (WHERE state = 'registered') as registered_users,
        COUNT(*) FILTER (WHERE registration_date >= CURRENT_DATE) as users_today
    FROM users;
END;
$$ LANGUAGE plpgsql;

-- Примеры вставки тестовых данных (раскомментируйте при необходимости)
/*
-- Добавление тестовых email адресов
INSERT INTO allowed_emails (email) VALUES 
    ('test@example.com'),
    ('user@test.com'),
    ('demo@gmail.com'),
    ('admin@company.com')
ON CONFLICT (email) DO NOTHING;
*/

-- Объединенная таблица ежедневного контента (сообщения + темы + вопросы)
CREATE TABLE IF NOT EXISTS daily_content (
    id BIGSERIAL PRIMARY KEY,
    day_of_month INTEGER NOT NULL CHECK (day_of_month >= 1 AND day_of_month <= 31),
    reminder_message TEXT NOT NULL,
    topic TEXT NOT NULL,
    question TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Уникальный индекс для дня месяца (один день - один набор контента)
CREATE UNIQUE INDEX IF NOT EXISTS idx_daily_content_day_active ON daily_content(day_of_month) WHERE is_active = true;

-- Таблица для отслеживания еженедельных лимитов постов
CREATE TABLE IF NOT EXISTS user_post_limits (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    week_start_date DATE NOT NULL,
    posts_generated INTEGER DEFAULT 0 NOT NULL,
    posts_limit INTEGER DEFAULT 10 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Уникальный индекс для пользователя и недели
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_post_limits_user_week ON user_post_limits(user_id, week_start_date);

-- Таблица истории сгенерированных постов
CREATE TABLE IF NOT EXISTS generated_posts (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    daily_content_id BIGINT REFERENCES daily_content(id),
    adapted_topic TEXT,
    user_question TEXT,
    user_answer TEXT,
    generated_content TEXT,
    week_start_date DATE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc'::text, NOW()) NOT NULL
);

-- Индексы для оптимизации запросов
CREATE INDEX IF NOT EXISTS idx_user_post_limits_user_id ON user_post_limits(user_id);
CREATE INDEX IF NOT EXISTS idx_user_post_limits_week ON user_post_limits(week_start_date);
CREATE INDEX IF NOT EXISTS idx_generated_posts_user_id ON generated_posts(user_id);
CREATE INDEX IF NOT EXISTS idx_generated_posts_week ON generated_posts(week_start_date);
CREATE INDEX IF NOT EXISTS idx_generated_posts_created_at ON generated_posts(created_at);
CREATE INDEX IF NOT EXISTS idx_daily_content_day ON daily_content(day_of_month);
CREATE INDEX IF NOT EXISTS idx_daily_content_active ON daily_content(is_active);

-- Триггер для автоматического обновления updated_at в таблице daily_content
DROP TRIGGER IF EXISTS update_daily_content_updated_at ON daily_content;
CREATE TRIGGER update_daily_content_updated_at
    BEFORE UPDATE ON daily_content
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Триггер для автоматического обновления updated_at в таблице user_post_limits
DROP TRIGGER IF EXISTS update_user_post_limits_updated_at ON user_post_limits;
CREATE TRIGGER update_user_post_limits_updated_at
    BEFORE UPDATE ON user_post_limits
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Добавление политик RLS для новых таблиц
ALTER TABLE daily_content ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_post_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE generated_posts ENABLE ROW LEVEL SECURITY;

-- Политики для новых таблиц (полный доступ для сервиса)
CREATE POLICY "Enable all access for service role" ON daily_content FOR ALL USING (true);
CREATE POLICY "Enable all access for service role" ON user_post_limits FOR ALL USING (true);
CREATE POLICY "Enable all access for service role" ON generated_posts FOR ALL USING (true);

-- Функция для получения начала недели
CREATE OR REPLACE FUNCTION get_week_start(input_date DATE DEFAULT CURRENT_DATE)
RETURNS DATE AS $$
BEGIN
    -- Возвращает понедельник текущей недели
    RETURN input_date - (EXTRACT(DOW FROM input_date)::INTEGER - 1);
END;
$$ LANGUAGE plpgsql;

-- Функция для проверки лимита постов пользователя
CREATE OR REPLACE FUNCTION check_user_post_limit(p_user_id BIGINT)
RETURNS TABLE (
    can_generate BOOLEAN,
    remaining_posts INTEGER,
    posts_generated INTEGER,
    posts_limit INTEGER
) AS $$
DECLARE
    current_week_start DATE;
    user_limit_record RECORD;
BEGIN
    current_week_start := get_week_start();
    
    -- Получаем или создаем запись лимита для текущей недели
    SELECT * INTO user_limit_record
    FROM user_post_limits
    WHERE user_id = p_user_id AND week_start_date = current_week_start;
    
    -- Если записи нет, создаем её
    IF user_limit_record IS NULL THEN
        INSERT INTO user_post_limits (user_id, week_start_date, posts_generated, posts_limit)
        VALUES (p_user_id, current_week_start, 0, 10)
        RETURNING * INTO user_limit_record;
    END IF;
    
    -- Возвращаем результат
    RETURN QUERY SELECT 
        (user_limit_record.posts_generated < user_limit_record.posts_limit) as can_generate,
        (user_limit_record.posts_limit - user_limit_record.posts_generated) as remaining_posts,
        user_limit_record.posts_generated,
        user_limit_record.posts_limit;
END;
$$ LANGUAGE plpgsql;

-- Функция для инкремента счетчика постов
CREATE OR REPLACE FUNCTION increment_user_post_count(p_user_id BIGINT)
RETURNS BOOLEAN AS $$
DECLARE
    current_week_start DATE;
    updated_rows INTEGER;
BEGIN
    current_week_start := get_week_start();
    
    -- Обновляем счетчик постов
    UPDATE user_post_limits 
    SET posts_generated = posts_generated + 1,
        updated_at = TIMEZONE('utc'::text, NOW())
    WHERE user_id = p_user_id 
      AND week_start_date = current_week_start
      AND posts_generated < posts_limit;
    
    GET DIAGNOSTICS updated_rows = ROW_COUNT;
    
    -- Если ничего не обновилось, возможно нужно создать запись или лимит превышен
    IF updated_rows = 0 THEN
        -- Проверяем, есть ли запись
        IF NOT EXISTS (
            SELECT 1 FROM user_post_limits 
            WHERE user_id = p_user_id AND week_start_date = current_week_start
        ) THEN
            -- Создаем новую запись
            INSERT INTO user_post_limits (user_id, week_start_date, posts_generated, posts_limit)
            VALUES (p_user_id, current_week_start, 1, 10);
            RETURN TRUE;
        ELSE
            -- Лимит превышен
            RETURN FALSE;
        END IF;
    END IF;
    
    RETURN TRUE;
END;
$$ LANGUAGE plpgsql;

-- Вставка базовых данных

-- Добавляем ежедневный контент на месяц (сообщения + темы + вопросы)
INSERT INTO daily_content (day_of_month, reminder_message, topic, question) VALUES 
(1, '<b>🌅 Доброе утро! Начинаем новый месяц!</b>

Время создать вдохновляющий пост для вашей аудитории в нише: <b>{niche}</b>

<i>Новый месяц - отличная возможность показать свежие идеи и тренды!</i>', 'Новые тренды и направления', 'Какие новые тренды вы заметили в вашей сфере за последнее время?'),

(2, '<b>⏰ Вторник - день опыта и кейсов!</b>

Подписчики ждут интересную историю от вас в нише: <b>{niche}</b>

<i>Реальные кейсы всегда вызывают больше всего откликов!</i>', 'Личный опыт и кейсы', 'Расскажите о недавнем проекте или задаче, которую вам удалось решить'),

(3, '<b>📚 Среда - время делиться знаниями!</b>

Сегодня отличный день для обучающего поста в нише: <b>{niche}</b>

<i>Помогите новичкам - они будут вам благодарны!</i>', 'Советы для начинающих', 'Какой совет вы бы дали тому, кто только начинает в вашей сфере?'),

(4, '<b>🤔 Четверг - анализируем ошибки!</b>

Время для полезного поста об ошибках в нише: <b>{niche}</b>

<i>Честность об ошибках делает вас более человечным и доверительным!</i>', 'Ошибки и уроки', 'Какую ошибку в вашей сфере вы считаете самой распространенной?'),

(5, '<b>🛠️ Пятница - рассказываем об инструментах!</b>

Поделитесь полезными ресурсами для ниши: <b>{niche}</b>

<i>Такие посты сохраняют и часто пересматривают!</i>', 'Инструменты и ресурсы', 'Какие инструменты или ресурсы вы используете в работе и можете порекомендовать?'),
(6, '<b>💪 Суббота - день мотивации!</b>

Поделитесь источником вдохновения с аудиторией в нише: <b>{niche}</b>

<i>Мотивационные посты в выходные получают особенно много откликов!</i>', 'Мотивация и вдохновение', 'Что вас мотивирует продолжать развиваться в вашей сфере?'),

(7, '<b>🔮 Воскресенье - смотрим в будущее!</b>

Время для прогнозов и инсайтов в нише: <b>{niche}</b>

<i>Люди любят читать предсказания и тренды в воскресенье!</i>', 'Прогнозы и будущее', 'Как, по вашему мнению, будет развиваться ваша сфера в ближайшие годы?'),

(8, '<b>⚖️ Понедельник - сравниваем подходы!</b>

Начнем неделю с аналитики в нише: <b>{niche}</b>

<i>Сравнения помогают аудитории лучше понять тему!</i>', 'Сравнение подходов', 'Какие существуют подходы к решению задач в вашей области и какой предпочитаете вы?'),

(9, '<b>📖 Вторник - день обучения!</b>

Поделитесь знаниями и ресурсами в нише: <b>{niche}</b>

<i>Образовательный контент всегда в тренде!</i>', 'Книги и обучение', 'Какие книги или курсы повлияли на ваше профессиональное развитие?'),

(10, '<b>🤝 Среда - день нетворкинга!</b>

Расскажите о важности связей в нише: <b>{niche}</b>

<i>Советы по нетворкингу очень ценят!</i>', 'Сетевое взаимодействие', 'Как вы строите профессиональные связи в вашей сфере?'),
(11, '<b>⚖️ Четверг - баланс и гармония!</b>

Время поговорить о work-life balance в нише: <b>{niche}</b>

<i>Тема баланса волнует всех - такие посты очень популярны!</i>', 'Баланс и отдых', 'Как вы поддерживаете баланс между работой и личной жизнью?'),

(12, '<b>🚀 Пятница - инновации и технологии!</b>

Поделитесь техническими инсайтами в нише: <b>{niche}</b>

<i>Технологический контент в пятницу заходит особенно хорошо!</i>', 'Технологии и инновации', 'Какие технологические решения меняют вашу сферу деятельности?'),

(13, '<b>👥 Суббота - фокус на аудитории!</b>

Расскажите о работе с клиентами в нише: <b>{niche}</b>

<i>Выходные - время для более личных тем!</i>', 'Клиенты и аудитория', 'Как вы понимаете потребности вашей целевой аудитории?'),

(14, '<b>🎯 Воскресенье - планируем и ставим цели!</b>

Поделитесь системой планирования в нише: <b>{niche}</b>

<i>Воскресенье - идеальный день для мотивации и планирования!</i>', 'Планирование и цели', 'Как вы планируете свою работу и ставите цели?'),

(15, '<b>💡 Понедельник - день креатива!</b>

Вдохновите аудиторию творческими идеями в нише: <b>{niche}</b>

<i>Начнем неделю с креативного подъема!</i>', 'Креативность и идеи', 'Откуда вы черпаете креативные идеи для своих проектов?'),
(16, '<b>⏰ Подписчики ждут ваш новый пост!</b>

Время создать интересный контент в нише: <b>{niche}</b>

<i>Регулярные публикации помогают развивать ваш личный бренд!</i>', 'Командная работа', 'Какие принципы командной работы считаете наиболее важными?'),
(17, '<b>⏰ Подписчики ждут ваш новый пост!</b>

Время создать интересный контент в нише: <b>{niche}</b>

<i>Регулярные публикации помогают развивать ваш личный бренд!</i>', 'Обратная связь', 'Как вы работаете с обратной связью от клиентов или коллег?'),
(18, '<b>⏰ Подписчики ждут ваш новый пост!</b>

Время создать интересный контент в нише: <b>{niche}</b>

<i>Регулярные публикации помогают развивать ваш личный бренд!</i>', 'Эффективность и продуктивность', 'Какие методы повышения эффективности вы используете?'),
(19, '<b>⏰ Подписчики ждут ваш новый пост!</b>

Время создать интересный контент в нише: <b>{niche}</b>

<i>Регулярные публикации помогают развивать ваш личный бренд!</i>', 'Этика и ценности', 'Какие этические принципы важны в вашей профессиональной деятельности?'),
(20, '<b>⏰ Подписчики ждут ваш новый пост!</b>

Время создать интересный контент в нише: <b>{niche}</b>

<i>Регулярные публикации помогают развивать ваш личный бренд!</i>', 'Конкуренция и позиционирование', 'Как вы выделяетесь среди конкурентов в вашей нише?'),
(21, '<b>⏰ Подписчики ждут ваш новый пост!</b>

Время создать интересный контент в нише: <b>{niche}</b>

<i>Регулярные публикации помогают развивать ваш личный бренд!</i>', 'Развитие и карьера', 'Какие шаги предпринимаете для профессионального роста?'),
(22, '<b>⏰ Подписчики ждут ваш новый пост!</b>

Время создать интересный контент в нише: <b>{niche}</b>

<i>Регулярные публикации помогают развивать ваш личный бренд!</i>', 'Проблемы и решения', 'С какими основными вызовами сталкиваются специалисты в вашей области?'),
(23, '<b>⏰ Подписчики ждут ваш новый пост!</b>

Время создать интересный контент в нише: <b>{niche}</b>

<i>Регулярные публикации помогают развивать ваш личный бренд!</i>', 'Качество и стандарты', 'Как вы обеспечиваете качество в своей работе?'),
(24, '<b>⏰ Подписчики ждут ваш новый пост!</b>

Время создать интересный контент в нише: <b>{niche}</b>

<i>Регулярные публикации помогают развивать ваш личный бренд!</i>', 'Автоматизация и оптимизация', 'Какие процессы в вашей работе можно автоматизировать?'),
(25, '<b>⏰ Подписчики ждут ваш новый пост!</b>

Время создать интересный контент в нише: <b>{niche}</b>

<i>Регулярные публикации помогают развивать ваш личный бренд!</i>', 'Коммуникация и презентации', 'Как вы презентуете свои идеи и результаты работы?'),
(26, '<b>⏰ Подписчики ждут ваш новый пост!</b>

Время создать интересный контент в нише: <b>{niche}</b>

<i>Регулярные публикации помогают развивать ваш личный бренд!</i>', 'Исследования и аналитика', 'Как вы изучаете и анализируете информацию в вашей сфере?'),
(27, '<b>⏰ Подписчики ждут ваш новый пост!</b>

Время создать интересный контент в нише: <b>{niche}</b>

<i>Регулярные публикации помогают развивать ваш личный бренд!</i>', 'Риски и безопасность', 'Какие риски существуют в вашей сфере и как их минимизировать?'),
(28, '<b>⏰ Подписчики ждут ваш новый пост!</b>

Время создать интересный контент в нише: <b>{niche}</b>

<i>Регулярные публикации помогают развивать ваш личный бренд!</i>', 'Глобальные тенденции', 'Как глобальные изменения влияют на вашу сферу деятельности?'),
(29, '<b>⏰ Подписчики ждут ваш новый пост!</b>

Время создать интересный контент в нише: <b>{niche}</b>

<i>Регулярные публикации помогают развивать ваш личный бренд!</i>', 'Личный бренд', 'Как вы развиваете и позиционируете свой личный бренд?'),
(30, '<b>⏰ Подписчики ждут ваш новый пост!</b>

Время создать интересный контент в нише: <b>{niche}</b>

<i>Регулярные публикации помогают развивать ваш личный бренд!</i>', 'Результаты и метрики', 'Как вы измеряете успешность своей работы?'),
(31, '<b>🎉 Последний день месяца!</b>

Время подвести итоги и поделиться планами в нише: <b>{niche}</b>

<i>Итоговые посты всегда получают много взаимодействий!</i>', 'Планы на будущее', 'Какие у вас планы и цели на следующий месяц?')
ON CONFLICT DO NOTHING;

-- Комментарии к таблицам
COMMENT ON TABLE allowed_emails IS 'Таблица разрешенных email адресов для регистрации';
COMMENT ON TABLE users IS 'Основная таблица пользователей Telegram бота';
COMMENT ON TABLE user_actions IS 'Логи действий пользователей для аналитики';
COMMENT ON TABLE daily_content IS 'Объединенная таблица ежедневного контента: сообщения напоминания + темы + вопросы для каждого дня месяца';
COMMENT ON TABLE user_post_limits IS 'Еженедельные лимиты постов для каждого пользователя';
COMMENT ON TABLE generated_posts IS 'История всех сгенерированных постов';

COMMENT ON COLUMN users.state IS 'Состояние пользователя в процессе регистрации (waiting_email, waiting_niche_description, registered, etc.)';
COMMENT ON COLUMN users.niche IS 'Определенная ниша деятельности пользователя';
COMMENT ON COLUMN users.subscription_status IS 'Статус подписки (inactive, active, expired)';
COMMENT ON COLUMN users.reminder_enabled IS 'Включены ли ежедневные напоминания';
COMMENT ON COLUMN users.reminder_time IS 'Время отправки напоминаний';
COMMENT ON COLUMN users.timezone IS 'Часовой пояс пользователя для корректной отправки напоминаний';
COMMENT ON COLUMN daily_content.day_of_month IS 'День месяца (1-31) для которого предназначен контент';
COMMENT ON COLUMN daily_content.reminder_message IS 'Текст напоминания для данного дня с HTML форматированием';
COMMENT ON COLUMN daily_content.topic IS 'Универсальная тема, которая будет адаптирована под нишу пользователя';
COMMENT ON COLUMN daily_content.question IS 'Вопрос, который задается пользователю для генерации поста по теме';
COMMENT ON COLUMN user_post_limits.week_start_date IS 'Дата начала недели (понедельник)';
COMMENT ON COLUMN user_post_limits.posts_generated IS 'Количество сгенерированных постов на текущей неделе';
COMMENT ON COLUMN user_post_limits.posts_limit IS 'Лимит постов на неделю (по умолчанию 10)';
