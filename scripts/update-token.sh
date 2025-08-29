#!/bin/bash

# Скрипт для быстрого обновления Telegram токена
# Usage: ./scripts/update-token.sh [новый_токен]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# Проверяем .env файл
if [[ ! -f ".env" ]]; then
    log_error "Файл .env не найден"
    log_info "Используйте: ./scripts/setup-env.sh"
    exit 1
fi

# Получаем новый токен
if [[ -n "$1" ]]; then
    NEW_TOKEN="$1"
else
    echo
    log_info "🤖 Обновление Telegram Bot Token"
    echo
    echo -e "${CYAN}Как получить новый токен:${NC}"
    echo "1. Найдите @BotFather в Telegram"
    echo "2. Отправьте /newbot для создания нового бота"
    echo "3. Или /mybots для управления существующими ботами"
    echo "4. Скопируйте токен вида: 1234567890:ABCDEFghijklmnopqrstuvwxyz"
    echo
    
    # Показываем текущий токен (замаскированный)
    current_token=$(grep "^TELEGRAM_BOT_TOKEN=" .env 2>/dev/null | cut -d'=' -f2- || echo "")
    if [[ -n "$current_token" ]]; then
        masked_token="${current_token:0:10}...${current_token: -10}"
        log_info "Текущий токен: $masked_token"
    fi
    
    echo
    read -p "Введите новый Telegram Bot Token: " NEW_TOKEN
fi

# Проверяем формат токена
if [[ ! "$NEW_TOKEN" =~ ^[0-9]+:[A-Za-z0-9_-]{35}$ ]]; then
    log_error "Неправильный формат токена"
    log_info "Токен должен выглядеть как: 1234567890:ABCDEFghijklmnopqrstuvwxyz"
    exit 1
fi

# Создаем бэкап
cp .env .env.backup
log_info "Создан бэкап: .env.backup"

# Обновляем токен
if grep -q "^TELEGRAM_BOT_TOKEN=" .env; then
    # Заменяем существующую строку
    sed -i "s/^TELEGRAM_BOT_TOKEN=.*/TELEGRAM_BOT_TOKEN=${NEW_TOKEN}/" .env
else
    # Добавляем новую строку
    echo "TELEGRAM_BOT_TOKEN=${NEW_TOKEN}" >> .env
fi

log_success "✅ Токен обновлен в .env"

# Перезапускаем бота
echo
log_info "🔄 Перезапускаем бота с новым токеном..."

if command -v docker-compose &> /dev/null; then
    docker-compose down
    docker-compose up -d
    
    # Ждем и проверяем
    sleep 5
    log_info "🔍 Проверяем подключение к Telegram..."
    
    # Проверяем логи на наличие ошибок
    if docker logs innokentiy-bot 2>&1 | grep -q "401 Unauthorized"; then
        log_error "❌ Токен отклонен Telegram сервером"
        log_info "Восстанавливаем старый токен..."
        mv .env.backup .env
        docker-compose down
        docker-compose up -d
        exit 1
    elif docker logs innokentiy-bot 2>&1 | grep -q "Запуск Telegram бота..."; then
        log_success "🎉 Бот успешно запущен с новым токеном!"
        rm .env.backup
    else
        log_warning "⚠️ Не удалось определить статус. Проверьте логи:"
        log_info "docker logs innokentiy-bot"
    fi
else
    log_warning "Docker Compose не найден. Перезапустите бота вручную."
fi

echo
log_info "💡 Полезные команды:"
echo "  ./scripts/status.sh     - проверить статус"
echo "  ./scripts/logs.sh       - просмотр логов"
echo "  ./scripts/restart.sh    - перезапуск"
