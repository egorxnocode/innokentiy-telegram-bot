#!/bin/bash

# Скрипт развертывания Telegram бота
# Usage: ./scripts/deploy.sh [production|staging]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Функции для цветного вывода
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

# Проверка аргументов
ENVIRONMENT=${1:-production}

if [[ "$ENVIRONMENT" != "production" && "$ENVIRONMENT" != "staging" ]]; then
    log_error "Неверное окружение. Используйте: production или staging"
    exit 1
fi

log_info "🚀 Начинаем развертывание в окружении: $ENVIRONMENT"

# Проверка наличия Docker
if ! command -v docker &> /dev/null; then
    log_error "Docker не установлен"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    log_error "Docker Compose не установлен"
    exit 1
fi

# Проверка конфигурации
if [[ ! -f ".env" ]]; then
    log_error "Файл .env не найден"
    log_info "Скопируйте env.example в .env и заполните переменные"
    log_info "Или используйте: ./scripts/setup-env.sh"
    exit 1
fi

# Проверка обязательных переменных
log_info "📋 Проверяем конфигурацию..."
required_vars=(
    "TELEGRAM_BOT_TOKEN"
    "SUPABASE_KEY"
    "ADMIN_CHAT_ID"
)

optional_vars=(
    "OPENAI_API_KEY"
    "N8N_NICHE_WEBHOOK_URL"
    "N8N_TOPIC_WEBHOOK_URL" 
    "N8N_POST_WEBHOOK_URL"
)

source .env

# Проверяем обязательные переменные
for var in "${required_vars[@]}"; do
    if [[ -z "${!var}" || "${!var}" == "your_"* ]]; then
        log_error "Переменная $var не задана в .env"
        log_info "Используйте: ./scripts/setup-env.sh для настройки"
        exit 1
    fi
done

# Предупреждаем о необязательных переменных
for var in "${optional_vars[@]}"; do
    if [[ -z "${!var}" || "${!var}" == "your_"* ]]; then
        log_warning "Переменная $var не настроена (необязательная)"
    fi
done

log_success "Конфигурация проверена"

# Создание сети для внешних сервисов если её нет
log_info "🌐 Проверяем Docker сети..."
if ! docker network ls | grep -q "services-network"; then
    log_info "Создаем сеть services-network..."
    docker network create services-network
    log_success "Сеть services-network создана"
else
    log_info "Сеть services-network уже существует"
fi

# Создание папки для логов
log_info "📁 Создаем папки..."
mkdir -p logs
chmod 755 logs

# Остановка существующих контейнеров
log_info "🛑 Останавливаем существующие контейнеры..."
docker-compose down --remove-orphans || true

# Сборка образа
log_info "🔨 Собираем Docker образ..."
docker-compose build --no-cache

# Запуск контейнеров
log_info "🚀 Запускаем контейнеры..."
docker-compose up -d

# Ожидание запуска
log_info "⏳ Ожидаем запуск сервисов..."
sleep 10

# Проверка health check
log_info "🔍 Проверяем состояние бота..."
max_attempts=30
attempt=1

while [[ $attempt -le $max_attempts ]]; do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        log_success "Бот успешно запущен и отвечает на health check"
        break
    fi
    
    if [[ $attempt -eq $max_attempts ]]; then
        log_error "Бот не отвечает на health check после $max_attempts попыток"
        log_info "Проверьте логи: docker-compose logs"
        exit 1
    fi
    
    log_info "Попытка $attempt/$max_attempts..."
    sleep 2
    ((attempt++))
done

# Показ статуса
log_info "📊 Статус контейнеров:"
docker-compose ps

# Показ логов
log_info "📋 Последние логи:"
docker-compose logs --tail=20

log_success "🎉 Развертывание завершено успешно!"
log_info "Для просмотра логов: ./scripts/logs.sh"
log_info "Для остановки: ./scripts/stop.sh"
log_info "Для рестарта: ./scripts/restart.sh"
