#!/bin/bash

# Скрипт резервного копирования конфигурации и логов
# Usage: ./scripts/backup.sh

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

# Создание имени бэкапа с датой
BACKUP_DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="backups"
BACKUP_NAME="innokentiy_bot_backup_$BACKUP_DATE"
BACKUP_PATH="$BACKUP_DIR/$BACKUP_NAME"

log_info "💾 Создаем резервную копию..."

# Создание папки для бэкапов
mkdir -p "$BACKUP_DIR"

# Создание временной папки для бэкапа
mkdir -p "$BACKUP_PATH"

# Копирование конфигурации
log_info "📋 Копируем конфигурацию..."
if [[ -f "config.env" ]]; then
    cp config.env "$BACKUP_PATH/"
    log_success "config.env скопирован"
else
    log_warning "config.env не найден"
fi

# Копирование важных файлов
log_info "📁 Копируем важные файлы..."
important_files=(
    "docker-compose.yml"
    "Dockerfile"
    ".dockerignore"
    "requirements.txt"
    "database_schema.sql"
)

for file in "${important_files[@]}"; do
    if [[ -f "$file" ]]; then
        cp "$file" "$BACKUP_PATH/"
        echo "  ✅ $file"
    else
        echo "  ⚠️ $file не найден"
    fi
done

# Копирование логов
log_info "📋 Копируем логи..."
if [[ -d "logs" ]] && [[ "$(ls -A logs)" ]]; then
    cp -r logs "$BACKUP_PATH/"
    log_size=$(du -h "$BACKUP_PATH/logs" | tail -1 | cut -f1)
    log_success "Логи скопированы ($log_size)"
else
    log_warning "Логи отсутствуют или пусты"
fi

# Экспорт Docker образа
log_info "🐳 Экспортируем Docker образ..."
if docker images | grep -q "innokentiy-bot_telegram-bot"; then
    docker save innokentiy-bot_telegram-bot > "$BACKUP_PATH/docker_image.tar"
    image_size=$(du -h "$BACKUP_PATH/docker_image.tar" | cut -f1)
    log_success "Docker образ экспортирован ($image_size)"
else
    log_warning "Docker образ не найден"
fi

# Создание информационного файла
log_info "📝 Создаем информационный файл..."
cat > "$BACKUP_PATH/backup_info.txt" << EOF
Резервная копия Innokentiy Bot
==============================

Дата создания: $(date)
Версия: $(git describe --tags 2>/dev/null || echo "unknown")
Коммит: $(git rev-parse HEAD 2>/dev/null || echo "unknown")

Содержимое бэкапа:
- config.env (конфигурация)
- docker-compose.yml (Docker Compose файл)
- Dockerfile (Docker образ конфигурация)
- requirements.txt (Python зависимости)
- database_schema.sql (схема базы данных)
- logs/ (логи приложения)
- docker_image.tar (Docker образ)

Восстановление:
1. Распакуйте архив в новую папку
2. Настройте config.env под новое окружение
3. Загрузите Docker образ: docker load < docker_image.tar
4. Запустите: docker-compose up -d

Примечания:
- Настройки Supabase и N8N нужно восстановить отдельно
- Убедитесь что все внешние сервисы доступны
EOF

# Создание архива
log_info "🗜️ Создаем архив..."
cd "$BACKUP_DIR"
tar -czf "$BACKUP_NAME.tar.gz" "$BACKUP_NAME"
cd ..

# Удаление временной папки
rm -rf "$BACKUP_PATH"

# Информация о бэкапе
BACKUP_FILE="$BACKUP_DIR/$BACKUP_NAME.tar.gz"
BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)

log_success "✅ Резервная копия создана!"
log_info "📁 Файл: $BACKUP_FILE"
log_info "📊 Размер: $BACKUP_SIZE"

# Показ всех бэкапов
log_info "📋 Все резервные копии:"
ls -lh "$BACKUP_DIR"/*.tar.gz 2>/dev/null || log_warning "Других бэкапов нет"

# Рекомендации
echo ""
log_info "💡 Рекомендации:"
echo "  - Сохраните бэкап в безопасном месте"
echo "  - Регулярно создавайте бэкапы"
echo "  - Тестируйте восстановление"
echo "  - Для восстановления используйте: ./scripts/restore.sh $BACKUP_NAME.tar.gz"

# Автоочистка старых бэкапов (оставляем последние 5)
OLD_BACKUPS=$(ls -t "$BACKUP_DIR"/*.tar.gz 2>/dev/null | tail -n +6)
if [[ -n "$OLD_BACKUPS" ]]; then
    log_info "🧹 Удаляем старые бэкапы (оставляем 5 последних)..."
    echo "$OLD_BACKUPS" | xargs rm -f
    log_success "Старые бэкапы удалены"
fi
