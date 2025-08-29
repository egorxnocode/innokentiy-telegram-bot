#!/bin/bash

# Скрипт для просмотра логов бота
# Usage: ./scripts/logs.sh [follow|tail|clear]

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

# Проверка что контейнер запущен
if ! docker-compose ps | grep -q "innokentiy-bot"; then
    log_error "Контейнер бота не запущен"
    log_info "Запустите бота: ./scripts/deploy.sh"
    exit 1
fi

ACTION=${1:-tail}

case $ACTION in
    "follow"|"f")
        log_info "📋 Следим за логами в реальном времени (Ctrl+C для выхода)..."
        docker-compose logs -f telegram-bot
        ;;
    
    "tail"|"t")
        LINES=${2:-50}
        log_info "📋 Показываем последние $LINES строк логов..."
        docker-compose logs --tail=$LINES telegram-bot
        ;;
    
    "clear"|"c")
        log_info "🗑️ Очищаем логи..."
        docker-compose down
        docker system prune -f --volumes
        rm -rf logs/*
        log_success "Логи очищены"
        log_info "Запустите бота заново: ./scripts/deploy.sh"
        ;;
    
    "all"|"a")
        log_info "📋 Показываем все логи..."
        docker-compose logs telegram-bot
        ;;
    
    "errors"|"e")
        log_info "🔴 Показываем только ошибки..."
        docker-compose logs telegram-bot 2>&1 | grep -i -E "(error|exception|traceback|failed)"
        ;;
    
    "stats"|"s")
        log_info "📊 Статистика логов..."
        echo "Всего строк логов: $(docker-compose logs telegram-bot 2>/dev/null | wc -l)"
        echo "Ошибок: $(docker-compose logs telegram-bot 2>&1 | grep -i -c -E "(error|exception)" || echo 0)"
        echo "Предупреждений: $(docker-compose logs telegram-bot 2>&1 | grep -i -c "warning" || echo 0)"
        echo "Размер файлов логов: $(du -h logs/ 2>/dev/null | tail -1 | cut -f1 || echo "0B")"
        ;;
    
    "help"|"h"|*)
        echo "📋 Управление логами Telegram бота"
        echo ""
        echo "Использование: ./scripts/logs.sh [команда]"
        echo ""
        echo "Команды:"
        echo "  follow, f     - Следить за логами в реальном времени"
        echo "  tail, t [N]   - Показать последние N строк (по умолчанию 50)"
        echo "  all, a        - Показать все логи"
        echo "  errors, e     - Показать только ошибки"
        echo "  clear, c      - Очистить все логи"
        echo "  stats, s      - Статистика логов"
        echo "  help, h       - Показать эту справку"
        echo ""
        echo "Примеры:"
        echo "  ./scripts/logs.sh follow    # Следить за логами"
        echo "  ./scripts/logs.sh tail 100  # Последние 100 строк"
        echo "  ./scripts/logs.sh errors    # Только ошибки"
        ;;
esac
