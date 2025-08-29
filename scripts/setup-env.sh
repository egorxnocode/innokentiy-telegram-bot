#!/bin/bash

# Скрипт для настройки .env файла
# Usage: ./scripts/setup-env.sh

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
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

log_question() {
    echo -e "${CYAN}[?]${NC} $1"
}

# Функция для ввода переменной
ask_variable() {
    local var_name=$1
    local description=$2
    local default_value=$3
    local current_value=""
    
    # Проверяем текущее значение
    if [[ -f ".env" ]]; then
        current_value=$(grep "^${var_name}=" .env 2>/dev/null | cut -d'=' -f2- || echo "")
    fi
    
    if [[ -n "$current_value" && "$current_value" != "your_"* ]]; then
        log_info "Текущее значение $var_name: ${current_value:0:20}..."
        read -p "Изменить? (y/N): " change_it
        if [[ ! "$change_it" =~ ^[Yy]$ ]]; then
            echo "$current_value"
            return
        fi
    fi
    
    echo
    log_question "$description"
    if [[ -n "$default_value" ]]; then
        echo -e "${YELLOW}По умолчанию: $default_value${NC}"
    fi
    
    read -p "Введите значение: " input_value
    
    if [[ -z "$input_value" && -n "$default_value" ]]; then
        echo "$default_value"
    else
        echo "$input_value"
    fi
}

# Главная функция
main() {
    log_info "🔧 Настройка файла .env для Innokentiy Telegram Bot"
    echo
    
    # Создаем .env из примера если его нет
    if [[ ! -f ".env" ]]; then
        if [[ -f "env.example" ]]; then
            cp env.example .env
            log_success "Создан .env файл из env.example"
        else
            log_error "Файл env.example не найден"
            exit 1
        fi
    fi
    
    # Собираем переменные
    declare -A env_vars
    
    log_info "📋 Настройка обязательных переменных:"
    
    # Telegram Bot Token
    env_vars[TELEGRAM_BOT_TOKEN]=$(ask_variable "TELEGRAM_BOT_TOKEN" \
        "Telegram Bot Token (получить у @BotFather в Telegram)" \
        "")
    
    # Admin Chat ID
    env_vars[ADMIN_CHAT_ID]=$(ask_variable "ADMIN_CHAT_ID" \
        "Ваш Telegram Chat ID (получить у @userinfobot)" \
        "")
    
    # Supabase Key
    env_vars[SUPABASE_KEY]=$(ask_variable "SUPABASE_KEY" \
        "Supabase API Key (из http://localhost:8000 -> Settings -> API)" \
        "")
    
    echo
    log_info "📋 Настройка дополнительных переменных:"
    
    # OpenAI API Key
    env_vars[OPENAI_API_KEY]=$(ask_variable "OPENAI_API_KEY" \
        "OpenAI API Key для транскрипции голосовых (с https://platform.openai.com)" \
        "")
    
    # N8N Webhooks
    env_vars[N8N_NICHE_WEBHOOK_URL]=$(ask_variable "N8N_NICHE_WEBHOOK_URL" \
        "N8N Webhook URL для определения ниши" \
        "http://localhost:5678/webhook/niche")
    
    env_vars[N8N_TOPIC_WEBHOOK_URL]=$(ask_variable "N8N_TOPIC_WEBHOOK_URL" \
        "N8N Webhook URL для адаптации темы" \
        "http://localhost:5678/webhook/topic")
    
    env_vars[N8N_POST_WEBHOOK_URL]=$(ask_variable "N8N_POST_WEBHOOK_URL" \
        "N8N Webhook URL для генерации поста" \
        "http://localhost:5678/webhook/post")
    
    # Создаем временный файл
    temp_file=$(mktemp)
    
    # Копируем .env в временный файл
    cp .env "$temp_file"
    
    # Обновляем переменные
    for var_name in "${!env_vars[@]}"; do
        var_value="${env_vars[$var_name]}"
        if [[ -n "$var_value" ]]; then
            # Удаляем старую строку и добавляем новую
            sed -i "/^${var_name}=/d" "$temp_file"
            echo "${var_name}=${var_value}" >> "$temp_file"
        fi
    done
    
    # Заменяем оригинальный файл
    mv "$temp_file" .env
    
    echo
    log_success "✅ Файл .env обновлен!"
    log_info "Проверьте настройки:"
    echo
    
    # Показываем итоговый результат
    echo -e "${CYAN}=== Настроенные переменные ===${NC}"
    for var_name in TELEGRAM_BOT_TOKEN ADMIN_CHAT_ID SUPABASE_KEY OPENAI_API_KEY; do
        value=$(grep "^${var_name}=" .env 2>/dev/null | cut -d'=' -f2- || echo "не задано")
        if [[ "$value" == "your_"* ]]; then
            value="не задано"
        fi
        printf "%-20s: %s\n" "$var_name" "${value:0:30}..."
    done
    
    echo
    log_info "Для запуска бота используйте: ./scripts/deploy.sh"
}

# Проверяем права выполнения
if [[ ! -x "$0" ]]; then
    chmod +x "$0"
fi

# Запускаем
main "$@"
