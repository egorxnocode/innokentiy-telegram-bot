#!/bin/bash

# Скрипт проверки статуса бота
# Usage: ./scripts/status.sh

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

echo -e "${PURPLE}🤖 СТАТУС TELEGRAM БОТА${NC}"
echo -e "${PURPLE}========================${NC}"

# Проверка Docker
echo -e "\n${CYAN}🐳 Docker:${NC}"
if command -v docker &> /dev/null; then
    echo "  ✅ Docker установлен: $(docker --version | cut -d' ' -f3)"
else
    echo "  ❌ Docker не установлен"
    exit 1
fi

if command -v docker-compose &> /dev/null; then
    echo "  ✅ Docker Compose установлен: $(docker-compose --version | cut -d' ' -f3)"
else
    echo "  ❌ Docker Compose не установлен"
    exit 1
fi

# Проверка контейнеров
echo -e "\n${CYAN}📦 Контейнеры:${NC}"
if docker-compose ps | grep -q "innokentiy-bot"; then
    status=$(docker-compose ps telegram-bot | grep telegram-bot | awk '{print $4}')
    if [[ "$status" == "Up" ]]; then
        echo "  ✅ Контейнер бота запущен"
    else
        echo "  ⚠️ Контейнер бота: $status"
    fi
else
    echo "  ❌ Контейнер бота не найден"
fi

# Подробная информация о контейнерах
if docker-compose ps | grep -q "telegram-bot"; then
    echo -e "\n${CYAN}📊 Детальная информация:${NC}"
    docker-compose ps
fi

# Проверка health check
echo -e "\n${CYAN}❤️ Health Check:${NC}"
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    health_response=$(curl -s http://localhost:8080/health)
    echo "  ✅ Health check отвечает"
    echo "  📋 Ответ: $health_response"
else
    echo "  ❌ Health check не отвечает"
fi

# Проверка ресурсов
echo -e "\n${CYAN}💾 Использование ресурсов:${NC}"
if docker-compose ps | grep -q "innokentiy-bot"; then
    container_id=$(docker-compose ps -q telegram-bot)
    if [[ -n "$container_id" ]]; then
        stats=$(docker stats --no-stream --format "table {{.CPUPerc}}\t{{.MemUsage}}" $container_id | tail -1)
        echo "  📈 CPU/Memory: $stats"
    fi
fi

# Проверка логов
echo -e "\n${CYAN}📋 Логи (последние ошибки):${NC}"
if docker-compose ps | grep -q "innokentiy-bot"; then
    errors=$(docker-compose logs --tail=100 telegram-bot 2>&1 | grep -i -E "(error|exception)" | tail -3)
    if [[ -n "$errors" ]]; then
        echo "  ⚠️ Последние ошибки:"
        echo "$errors" | sed 's/^/    /'
    else
        echo "  ✅ Ошибок в последних 100 строках не найдено"
    fi
else
    echo "  ❌ Контейнер не запущен"
fi

# Проверка сетей
echo -e "\n${CYAN}🌐 Docker сети:${NC}"
if docker network ls | grep -q "services-network"; then
    echo "  ✅ Сеть services-network существует"
else
    echo "  ⚠️ Сеть services-network не найдена"
fi

# Проверка конфигурации
echo -e "\n${CYAN}⚙️ Конфигурация:${NC}"
if [[ -f "config.env" ]]; then
    echo "  ✅ Файл config.env найден"
    
    # Проверка основных переменных
    source config.env
    vars_check=(
        "TELEGRAM_BOT_TOKEN:Telegram Bot Token"
        "SUPABASE_URL:Supabase URL"
        "ADMIN_CHAT_ID:Admin Chat ID"
        "N8N_NICHE_WEBHOOK_URL:N8N Niche Webhook"
        "N8N_TOPIC_WEBHOOK_URL:N8N Topic Webhook"
        "N8N_POST_WEBHOOK_URL:N8N Post Webhook"
    )
    
    for var_check in "${vars_check[@]}"; do
        var_name="${var_check%%:*}"
        var_desc="${var_check##*:}"
        
        if [[ -n "${!var_name}" ]]; then
            echo "  ✅ $var_desc настроен"
        else
            echo "  ❌ $var_desc не настроен"
        fi
    done
else
    echo "  ❌ Файл config.env не найден"
fi

# Проверка файлов
echo -e "\n${CYAN}📁 Файлы и папки:${NC}"
important_files=(
    "main.py:Главный файл"
    "bot.py:Telegram Bot"
    "database.py:База данных"
    "requirements.txt:Зависимости"
    "Dockerfile:Docker файл"
    "docker-compose.yml:Docker Compose"
)

for file_check in "${important_files[@]}"; do
    file_name="${file_check%%:*}"
    file_desc="${file_check##*:}"
    
    if [[ -f "$file_name" ]]; then
        echo "  ✅ $file_desc найден"
    else
        echo "  ❌ $file_desc не найден"
    fi
done

if [[ -d "logs" ]]; then
    log_size=$(du -h logs/ 2>/dev/null | tail -1 | cut -f1 || echo "0B")
    echo "  📋 Папка логов: $log_size"
else
    echo "  📋 Папка логов будет создана при запуске"
fi

# Итоговый статус
echo -e "\n${PURPLE}🎯 ИТОГОВЫЙ СТАТУС:${NC}"

if docker-compose ps | grep -q "innokentiy-bot" && curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "  ${GREEN}✅ БОТ РАБОТАЕТ НОРМАЛЬНО${NC}"
    echo "  📋 Команды управления:"
    echo "    ./scripts/logs.sh follow    - Просмотр логов"
    echo "    ./scripts/restart.sh soft   - Перезапуск"
    echo "    ./scripts/stop.sh           - Остановка"
elif docker-compose ps | grep -q "innokentiy-bot"; then
    echo -e "  ${YELLOW}⚠️ БОТ ЗАПУЩЕН, НО ЕСТЬ ПРОБЛЕМЫ${NC}"
    echo "  🔍 Рекомендация: ./scripts/logs.sh errors"
else
    echo -e "  ${RED}❌ БОТ НЕ ЗАПУЩЕН${NC}"
    echo "  🚀 Рекомендация: ./scripts/deploy.sh"
fi
