#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для обновления статусов подписок существующих пользователей
"""

import asyncio
import logging
from database import Database

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Основная функция для обновления статусов"""
    try:
        logger.info("Начинаем обновление статусов подписок...")
        
        db = Database()
        
        # Обновляем статусы всех пользователей
        stats = await db.update_all_subscription_statuses()
        
        logger.info("Обновление завершено!")
        logger.info(f"Статистика:")
        logger.info(f"  - Переведено в неактивные: {stats['updated_to_inactive']}")
        logger.info(f"  - Оставлено активными: {stats['kept_active']}")
        logger.info(f"  - Ошибок: {stats['errors']}")
        
        if stats['errors'] > 0:
            logger.warning(f"Обнаружены ошибки при обновлении {stats['errors']} пользователей")
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
