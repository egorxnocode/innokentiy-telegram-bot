# -*- coding: utf-8 -*-
"""
Модуль для отправки уведомлений админу через отдельного бота
"""

import logging
import asyncio
from typing import Optional
from telegram import Bot
from telegram.error import TelegramError

from config import ADMIN_BOT_TOKEN, ADMIN_CHAT_ID, ENABLE_ADMIN_NOTIFICATIONS

logger = logging.getLogger(__name__)

class AdminNotifier:
    """Класс для отправки уведомлений админу через отдельного бота"""
    
    def __init__(self):
        self.admin_bot = None
        if ADMIN_BOT_TOKEN and ENABLE_ADMIN_NOTIFICATIONS:
            self.admin_bot = Bot(token=ADMIN_BOT_TOKEN)
        
    async def send_notification(self, message: str, parse_mode: str = 'HTML') -> bool:
        """
        Отправляет уведомление админу
        
        Args:
            message (str): Текст сообщения
            parse_mode (str): Режим парсинга (HTML или Markdown)
            
        Returns:
            bool: True если сообщение отправлено успешно
        """
        if not self.admin_bot or not ADMIN_CHAT_ID or not ENABLE_ADMIN_NOTIFICATIONS:
            logger.debug("Админские уведомления отключены или не настроены")
            return False
            
        try:
            await self.admin_bot.send_message(
                chat_id=ADMIN_CHAT_ID,
                text=message,
                parse_mode=parse_mode
            )
            logger.debug("Админское уведомление отправлено успешно")
            return True
            
        except TelegramError as e:
            logger.error(f"Ошибка отправки админского уведомления: {e}")
            return False
        except Exception as e:
            logger.error(f"Неожиданная ошибка при отправке админского уведомления: {e}")
            return False
    
    async def notify_n8n_error(self, webhook_type: str, error_code: int, error_details: str, 
                               user_info: Optional[dict] = None) -> bool:
        """
        Уведомляет админа об ошибке N8N
        
        Args:
            webhook_type (str): Тип webhook (niche, topic, post)
            error_code (int): HTTP код ошибки
            error_details (str): Детали ошибки
            user_info (dict, optional): Информация о пользователе
            
        Returns:
            bool: True если уведомление отправлено
        """
        from datetime import datetime
        
        # Формируем сообщение об ошибке
        message = f"""
🔴 <b>N8N Ошибка: {webhook_type}</b>

📝 <b>Описание:</b>
N8N вернул ошибку {error_code}

👤 <b>Пользователь:</b>
"""
        
        if user_info:
            message += f"""   • ID: {user_info.get('telegram_id', 'Неизвестно')}
   • Имя: {user_info.get('first_name', 'Неизвестно')}
   • Username: @{user_info.get('username', 'отсутствует')}
   • Ниша: {user_info.get('niche', 'Не определена')}
"""
        else:
            message += "   • Информация недоступна\n"
        
        message += f"""
🔍 <b>Детали ошибки:</b>
   • Тип webhook: {webhook_type}
   • HTTP код: {error_code}
   • Ошибка: {error_details}

🕒 <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
"""
        
        return await self.send_notification(message)
    
    async def notify_system_error(self, error_type: str, error_message: str, 
                                  additional_info: Optional[str] = None) -> bool:
        """
        Уведомляет админа о системной ошибке
        
        Args:
            error_type (str): Тип ошибки
            error_message (str): Сообщение об ошибке  
            additional_info (str, optional): Дополнительная информация
            
        Returns:
            bool: True если уведомление отправлено
        """
        from datetime import datetime
        
        message = f"""
⚠️ <b>Системная ошибка: {error_type}</b>

📝 <b>Описание:</b>
{error_message}
"""
        
        if additional_info:
            message += f"\n🔍 <b>Дополнительно:</b>\n{additional_info}"
        
        message += f"\n\n🕒 <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        
        return await self.send_notification(message)

# Глобальный экземпляр
admin_notifier = AdminNotifier()
