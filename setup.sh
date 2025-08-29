#!/bin/bash

# Скрипт быстрой настройки и развертывания Telegram бота
# Usage: ./setup.sh

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo -e "${PURPLE}🤖 НАСТРОЙКА INNOKENTIY TELEGRAM BOT${NC}"
echo -e "${PURPLE}====================================${NC}"

# Проверка требований
log_info "🔍 Проверяем системные требования..."

# Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker не установлен!"
    echo "Установите Docker: https://docs.docker.com/get-docker/"
    exit 1
fi
log_success "Docker найден: $(docker --version | cut -d' ' -f3)"

# Docker Compose
if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose не установлен!"
    echo "Установите Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi
log_success "Docker Compose найден: $(docker-compose --version | cut -d' ' -f3)"

# Проверка прав Docker
if ! docker ps &> /dev/null; then
    log_error "Нет прав для работы с Docker!"
    echo "Добавьте пользователя в группу docker: sudo usermod -aG docker \$USER"
    echo "Затем перелогиньтесь и запустите скрипт снова"
    exit 1
fi
log_success "Права Docker проверены"

# Создание конфигурации
log_info "⚙️ Настройка конфигурации..."

if [[ ! -f "config.env" ]]; then
    log_info "Создаем config.env из шаблона..."
    cp config.env.example config.env
    log_warning "Необходимо заполнить config.env!"
    
    echo ""
    echo -e "${CYAN}📋 Необходимые переменные:${NC}"
    echo "1. TELEGRAM_BOT_TOKEN - токен бота от @BotFather"
    echo "2. SUPABASE_URL - URL вашего Supabase проекта"
    echo "3. SUPABASE_KEY - ключ Supabase"
    echo "4. OPENAI_API_KEY - ключ OpenAI для транскрибации"
    echo "5. N8N_*_WEBHOOK_URL - URL ваших N8N вебхуков"
    echo "6. ADMIN_CHAT_ID - ID чата для админских уведомлений"
    echo ""
    echo -e "${YELLOW}⚠️ Отредактируйте config.env и запустите скрипт снова${NC}"
    echo "Команда: nano config.env"
    exit 1
else
    log_success "config.env найден"
fi

# Проверка конфигурации
log_info "🔍 Проверяем конфигурацию..."
source config.env

required_vars=(
    "TELEGRAM_BOT_TOKEN"
    "SUPABASE_URL"
    "SUPABASE_KEY"
    "OPENAI_API_KEY"
    "ADMIN_CHAT_ID"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        missing_vars+=("$var")
    fi
done

if [[ ${#missing_vars[@]} -gt 0 ]]; then
    log_error "Не заполнены обязательные переменные:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Отредактируйте config.env и заполните все переменные"
    exit 1
fi

log_success "Обязательные переменные заполнены"

# Проверка N8N вебхуков
webhook_vars=(
    "N8N_NICHE_WEBHOOK_URL"
    "N8N_TOPIC_WEBHOOK_URL"
    "N8N_POST_WEBHOOK_URL"
)

missing_webhooks=()
for var in "${webhook_vars[@]}"; do
    if [[ -z "${!var}" ]]; then
        missing_webhooks+=("$var")
    fi
done

if [[ ${#missing_webhooks[@]} -gt 0 ]]; then
    log_warning "Не настроены N8N вебхуки:"
    for var in "${missing_webhooks[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Бот будет работать, но без функций N8N"
    read -p "Продолжить? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Настройте N8N вебхуки в config.env"
        exit 1
    fi
fi

# Создание необходимых папок
log_info "📁 Создаем необходимые папки..."
mkdir -p logs
mkdir -p backups
chmod 755 scripts/*.sh 2>/dev/null || true

# Создание Docker сети
log_info "🌐 Настройка Docker сети..."
if ! docker network ls | grep -q "services-network"; then
    log_info "Создаем сеть services-network..."
    docker network create services-network
    log_success "Сеть services-network создана"
else
    log_info "Сеть services-network уже существует"
fi

# Проверка подключения к внешним сервисам
log_info "🔗 Проверяем подключение к сервисам..."

# Проверка Supabase
if curl -s "$SUPABASE_URL/rest/v1/" -H "apikey: $SUPABASE_KEY" > /dev/null 2>&1; then
    log_success "Supabase доступен"
else
    log_warning "Supabase недоступен или неверные настройки"
fi

# Проверка OpenAI
if curl -s "https://api.openai.com/v1/models" -H "Authorization: Bearer $OPENAI_API_KEY" > /dev/null 2>&1; then
    log_success "OpenAI API доступен"
else
    log_warning "OpenAI API недоступен или неверный ключ"
fi

# Развертывание
echo ""
log_info "🚀 Готовы к развертыванию!"
echo ""
echo -e "${CYAN}Варианты запуска:${NC}"
echo "1. Полное развертывание (рекомендуется)"
echo "2. Только сборка образа"
echo "3. Пропустить и настроить вручную"
echo ""

read -p "Выберите вариант (1-3): " -n 1 -r
echo

case $REPLY in
    1)
        log_info "🚀 Запускаем полное развертывание..."
        ./scripts/deploy.sh
        ;;
    2)
        log_info "🔨 Собираем Docker образ..."
        docker-compose build
        log_success "Образ собран! Запустите: ./scripts/deploy.sh"
        ;;
    3)
        log_info "⚙️ Настройка завершена"
        ;;
    *)
        log_warning "Неверный выбор. Запустите развертывание вручную: ./scripts/deploy.sh"
        ;;
esac

# Показ команд управления
echo ""
echo -e "${PURPLE}🎛️ КОМАНДЫ УПРАВЛЕНИЯ:${NC}"
echo -e "${CYAN}./scripts/deploy.sh${NC}    - Развертывание/запуск"
echo -e "${CYAN}./scripts/status.sh${NC}     - Проверка статуса"
echo -e "${CYAN}./scripts/logs.sh${NC}       - Просмотр логов"
echo -e "${CYAN}./scripts/restart.sh${NC}    - Перезапуск"
echo -e "${CYAN}./scripts/stop.sh${NC}       - Остановка"
echo -e "${CYAN}./scripts/backup.sh${NC}     - Создание бэкапа"

echo ""
echo -e "${GREEN}✅ Настройка завершена!${NC}"

if docker-compose ps | grep -q "innokentiy-bot"; then
    echo -e "${GREEN}🤖 Бот запущен и работает!${NC}"
    echo "Проверьте статус: ./scripts/status.sh"
else
    echo "Для запуска бота: ./scripts/deploy.sh"
fi
