#!/bin/bash

# Главный скрипт управления Innokentiy Telegram Bot
# Usage: ./scripts/bot.sh [команда]

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

show_header() {
    echo -e "${MAGENTA}"
    echo "╔══════════════════════════════════════════════════════════════╗"
    echo "║                 🤖 INNOKENTIY TELEGRAM BOT 🤖                ║"
    echo "║                     Система управления                       ║"
    echo "╚══════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

show_help() {
    show_header
    echo -e "${CYAN}Доступные команды:${NC}"
    echo
    echo -e "${GREEN}📋 Настройка и развертывание:${NC}"
    echo "  setup      - Настроить .env файл (интерактивно)"
    echo "  deploy     - Развернуть бота"
    echo "  token      - Обновить Telegram токен"
    echo
    echo -e "${GREEN}🎮 Управление:${NC}"
    echo "  start      - Запустить бота"
    echo "  stop       - Остановить бота"
    echo "  restart    - Перезапустить бота"
    echo "  status     - Показать статус"
    echo
    echo -e "${GREEN}📊 Мониторинг:${NC}"
    echo "  logs       - Показать логи"
    echo "  health     - Проверить health check"
    echo "  ps         - Показать Docker контейнеры"
    echo
    echo -e "${GREEN}🔧 Обслуживание:${NC}"
    echo "  update     - Обновить код с GitHub"
    echo "  rebuild    - Пересобрать образ"
    echo "  backup     - Создать бэкап конфигурации"
    echo "  clean      - Очистить Docker ресурсы"
    echo
    echo -e "${GREEN}ℹ️ Информация:${NC}"
    echo "  help       - Показать эту справку"
    echo "  version    - Показать версию"
    echo
    echo -e "${YELLOW}Примеры использования:${NC}"
    echo "  ./scripts/bot.sh setup     # Первоначальная настройка"
    echo "  ./scripts/bot.sh deploy    # Развертывание"
    echo "  ./scripts/bot.sh status    # Проверка статуса"
    echo "  ./scripts/bot.sh logs      # Просмотр логов"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}❌ Docker не установлен${NC}"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}❌ Docker Compose не установлен${NC}"
        exit 1
    fi
}

case "${1:-help}" in
    "setup"|"s")
        show_header
        echo -e "${BLUE}🔧 Настройка .env файла...${NC}"
        ./scripts/setup-env.sh
        ;;
    
    "deploy"|"d")
        show_header
        echo -e "${BLUE}🚀 Развертывание бота...${NC}"
        check_docker
        ./scripts/deploy.sh
        ;;
    
    "token"|"t")
        show_header
        echo -e "${BLUE}🔑 Обновление Telegram токена...${NC}"
        ./scripts/update-token.sh "${2}"
        ;;
    
    "start")
        check_docker
        echo -e "${GREEN}▶️ Запуск бота...${NC}"
        docker-compose up -d
        echo -e "${GREEN}✅ Бот запущен${NC}"
        ;;
    
    "stop")
        check_docker
        echo -e "${YELLOW}⏹️ Остановка бота...${NC}"
        docker-compose down
        echo -e "${YELLOW}✅ Бот остановлен${NC}"
        ;;
    
    "restart"|"r")
        show_header
        echo -e "${BLUE}🔄 Перезапуск бота...${NC}"
        ./scripts/restart.sh "${2:-soft}"
        ;;
    
    "status"|"st")
        show_header
        ./scripts/status.sh
        ;;
    
    "logs"|"l")
        check_docker
        if [[ -n "$2" ]]; then
            docker logs "innokentiy-bot" --tail "$2" -f
        else
            ./scripts/logs.sh
        fi
        ;;
    
    "health"|"h")
        echo -e "${BLUE}🔍 Проверка health check...${NC}"
        if curl -s http://localhost:8080/health | jq . 2>/dev/null; then
            echo -e "${GREEN}✅ Health check OK${NC}"
        else
            echo -e "${RED}❌ Health check failed${NC}"
            exit 1
        fi
        ;;
    
    "ps")
        check_docker
        echo -e "${BLUE}📊 Docker контейнеры:${NC}"
        docker-compose ps
        ;;
    
    "update"|"u")
        echo -e "${BLUE}📥 Обновление с GitHub...${NC}"
        git pull origin main
        echo -e "${GREEN}✅ Код обновлен${NC}"
        echo -e "${YELLOW}💡 Используйте 'rebuild' для применения изменений${NC}"
        ;;
    
    "rebuild"|"rb")
        show_header
        echo -e "${BLUE}🔨 Пересборка образа...${NC}"
        check_docker
        ./scripts/restart.sh hard
        ;;
    
    "backup"|"b")
        echo -e "${BLUE}💾 Создание бэкапа...${NC}"
        backup_dir="backup_$(date +%Y%m%d_%H%M%S)"
        mkdir -p "$backup_dir"
        
        # Копируем важные файлы
        [[ -f ".env" ]] && cp .env "$backup_dir/"
        [[ -f "docker-compose.yml" ]] && cp docker-compose.yml "$backup_dir/"
        [[ -d "logs" ]] && cp -r logs "$backup_dir/"
        
        echo -e "${GREEN}✅ Бэкап создан: $backup_dir${NC}"
        ;;
    
    "clean"|"c")
        echo -e "${YELLOW}🧹 Очистка Docker ресурсов...${NC}"
        check_docker
        docker system prune -f
        docker volume prune -f
        echo -e "${GREEN}✅ Очистка завершена${NC}"
        ;;
    
    "version"|"v")
        show_header
        echo -e "${CYAN}📋 Информация о системе:${NC}"
        echo "  Git commit: $(git rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
        echo "  Git branch: $(git branch --show-current 2>/dev/null || echo 'unknown')"
        echo "  Docker: $(docker --version 2>/dev/null || echo 'not installed')"
        echo "  Docker Compose: $(docker-compose --version 2>/dev/null || echo 'not installed')"
        ;;
    
    "help"|*)
        show_help
        ;;
esac
