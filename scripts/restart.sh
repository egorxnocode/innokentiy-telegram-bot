#!/bin/bash

# Скрипт перезапуска бота
# Usage: ./scripts/restart.sh [hard|soft]

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

RESTART_TYPE=${1:-soft}

case $RESTART_TYPE in
    "hard"|"h")
        log_info "🔄 Жесткий перезапуск (пересборка образа)..."
        
        # Остановка контейнеров
        log_info "🛑 Останавливаем контейнеры..."
        docker-compose down
        
        # Удаление образа
        log_info "🗑️ Удаляем старый образ..."
        docker rmi innokentiy-bot_telegram-bot 2>/dev/null || true
        
        # Очистка Docker cache
        log_info "🧹 Очищаем Docker cache..."
        docker system prune -f
        
        # Пересборка и запуск
        log_info "🔨 Пересобираем и запускаем..."
        docker-compose build --no-cache
        docker-compose up -d
        ;;
    
    "soft"|"s")
        log_info "🔄 Мягкий перезапуск..."
        
        # Просто перезапуск контейнера
        docker-compose restart telegram-bot
        ;;
    
    "config"|"c")
        log_info "🔄 Перезапуск с обновлением конфигурации..."
        
        # Остановка
        docker-compose down
        
        # Проверка конфигурации
        if [[ ! -f "config.env" ]]; then
            log_error "Файл config.env не найден"
            exit 1
        fi
        
        # Запуск с новой конфигурацией
        docker-compose up -d
        ;;
    
    "help"|*)
        echo "🔄 Перезапуск Telegram бота"
        echo ""
        echo "Использование: ./scripts/restart.sh [тип]"
        echo ""
        echo "Типы перезапуска:"
        echo "  soft, s    - Мягкий перезапуск контейнера (по умолчанию)"
        echo "  hard, h    - Жесткий перезапуск с пересборкой образа"
        echo "  config, c  - Перезапуск с обновлением конфигурации"
        echo "  help       - Показать эту справку"
        echo ""
        echo "Примеры:"
        echo "  ./scripts/restart.sh soft    # Быстрый перезапуск"
        echo "  ./scripts/restart.sh hard    # После изменения кода"
        echo "  ./scripts/restart.sh config  # После изменения config.env"
        exit 0
        ;;
esac

# Ожидание запуска
log_info "⏳ Ожидаем запуск сервисов..."
sleep 10

# Проверка health check
log_info "🔍 Проверяем состояние бота..."
max_attempts=15
attempt=1

while [[ $attempt -le $max_attempts ]]; do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        log_success "Бот успешно перезапущен"
        break
    fi
    
    if [[ $attempt -eq $max_attempts ]]; then
        log_error "Бот не отвечает на health check"
        log_info "Проверьте логи: ./scripts/logs.sh"
        exit 1
    fi
    
    log_info "Попытка $attempt/$max_attempts..."
    sleep 2
    ((attempt++))
done

# Показ статуса
log_info "📊 Статус контейнеров:"
docker-compose ps

log_success "✅ Перезапуск завершен успешно!"
