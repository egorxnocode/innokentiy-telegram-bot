#!/bin/bash

# Скрипт остановки бота
# Usage: ./scripts/stop.sh [clean]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

ACTION=${1:-normal}

case $ACTION in
    "clean"|"c")
        log_info "🧹 Полная остановка с очисткой..."
        
        # Остановка и удаление контейнеров
        log_info "🛑 Останавливаем и удаляем контейнеры..."
        docker-compose down --remove-orphans --volumes
        
        # Удаление образов
        log_info "🗑️ Удаляем образы..."
        docker rmi innokentiy-bot_telegram-bot 2>/dev/null || true
        
        # Очистка неиспользуемых ресурсов
        log_info "🧽 Очищаем Docker ресурсы..."
        docker system prune -f --volumes
        
        log_success "Полная очистка завершена"
        ;;
    
    "normal"|"n"|*)
        log_info "🛑 Останавливаем бота..."
        
        # Проверка что контейнер запущен
        if ! docker-compose ps | grep -q "innokentiy-bot"; then
            log_warning "Контейнер уже остановлен"
            exit 0
        fi
        
        # Graceful shutdown
        log_info "📋 Отправляем сигнал graceful shutdown..."
        docker-compose kill -s SIGTERM telegram-bot
        
        # Ждем немного для graceful shutdown
        sleep 5
        
        # Принудительная остановка если нужно
        log_info "🛑 Останавливаем контейнеры..."
        docker-compose down
        
        log_success "Бот остановлен"
        ;;
esac

# Показ статуса
log_info "📊 Статус контейнеров:"
docker-compose ps

if [[ "$ACTION" != "clean" ]]; then
    log_info "Для запуска: ./scripts/deploy.sh"
    log_info "Для полной очистки: ./scripts/stop.sh clean"
fi
