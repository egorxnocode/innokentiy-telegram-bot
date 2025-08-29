# -*- coding: utf-8 -*-
"""
Система уведомлений для администратора
"""

import asyncio
import logging
import requests
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

from config import (
    TELEGRAM_BOT_TOKEN, ADMIN_CHAT_ID, ENABLE_ADMIN_NOTIFICATIONS, DEBUG
)

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """Уровни важности уведомлений"""
    INFO = "🔵"
    WARNING = "🟡" 
    ERROR = "🔴"
    CRITICAL = "🚨"

class AdminNotifier:
    """Класс для отправки уведомлений администратору"""
    
    def __init__(self):
        self.enabled = ENABLE_ADMIN_NOTIFICATIONS and TELEGRAM_BOT_TOKEN and ADMIN_CHAT_ID
        self.bot_token = TELEGRAM_BOT_TOKEN  # Используем основной бот
        self.chat_id = ADMIN_CHAT_ID
        
        if not self.enabled:
            logger.warning("Admin notifications disabled or not configured")
        elif self.enabled:
            logger.info(f"Admin notifications enabled, chat_id: {ADMIN_CHAT_ID}")
    
    async def send_notification(self, 
                              level: AlertLevel,
                              title: str,
                              message: str,
                              user_info: Optional[Dict[str, Any]] = None,
                              error_details: Optional[Dict[str, Any]] = None,
                              suggested_actions: Optional[list] = None) -> bool:
        """
        Отправляет уведомление администратору
        
        Args:
            level: Уровень важности
            title: Заголовок уведомления
            message: Основное сообщение
            user_info: Информация о пользователе
            error_details: Детали ошибки
            suggested_actions: Предлагаемые действия
            
        Returns:
            bool: True если уведомление отправлено успешно
        """
        if not self.enabled:
            logger.debug("Admin notifications disabled")
            return False
        
        try:
            # Формируем текст уведомления
            notification_text = self._format_notification(
                level, title, message, user_info, error_details, suggested_actions
            )
            
            # Отправляем через Telegram API
            success = await self._send_telegram_message(notification_text)
            
            if success:
                logger.info(f"Admin notification sent: {title}")
            else:
                logger.error(f"Failed to send admin notification: {title}")
                
            return success
            
        except Exception as e:
            logger.error(f"Error sending admin notification: {e}")
            return False
    
    def _format_notification(self,
                           level: AlertLevel,
                           title: str,
                           message: str,
                           user_info: Optional[Dict[str, Any]],
                           error_details: Optional[Dict[str, Any]],
                           suggested_actions: Optional[list]) -> str:
        """Форматирует текст уведомления"""
        
        # Заголовок с эмодзи уровня
        text = f"{level.value} <b>{title}</b>\n\n"
        
        # Основное сообщение
        text += f"📝 <b>Описание:</b>\n{message}\n\n"
        
        # Информация о пользователе
        if user_info:
            text += f"👤 <b>Пользователь:</b>\n"
            text += f"   • ID: <code>{user_info.get('telegram_id', 'N/A')}</code>\n"
            text += f"   • Имя: {user_info.get('first_name', 'N/A')}\n"
            text += f"   • Username: @{user_info.get('username', 'N/A')}\n"
            text += f"   • Ниша: {user_info.get('niche', 'N/A')}\n"
            text += f"   • Состояние: {user_info.get('state', 'N/A')}\n\n"
        
        # Детали ошибки
        if error_details:
            text += f"🔍 <b>Детали ошибки:</b>\n"
            for key, value in error_details.items():
                text += f"   • {key}: <code>{value}</code>\n"
            text += "\n"
        
        # Предлагаемые действия
        if suggested_actions:
            text += f"🎯 <b>Рекомендуемые действия:</b>\n"
            for i, action in enumerate(suggested_actions, 1):
                text += f"   {i}. {action}\n"
            text += "\n"
        
        # Временная метка
        text += f"🕒 <b>Время:</b> {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        
        return text
    
    async def _send_telegram_message(self, text: str) -> bool:
        """Отправляет сообщение через Telegram Bot API"""
        
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            
            payload = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            # Используем requests для синхронного запроса
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(url, json=payload, timeout=10)
            )
            
            if response.status_code == 200:
                return True
            else:
                logger.error(f"Telegram API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending telegram message: {e}")
            return False
    
    # Специализированные методы для разных типов ошибок
    
    async def notify_user_error(self,
                              error_type: str,
                              error_message: str,
                              user_info: Dict[str, Any],
                              traceback_info: Optional[str] = None) -> bool:
        """Уведомление об ошибке пользователя"""
        
        error_details = {
            "Тип ошибки": error_type,
            "Сообщение": error_message[:200] + "..." if len(error_message) > 200 else error_message
        }
        
        if traceback_info:
            error_details["Traceback"] = traceback_info[:300] + "..." if len(traceback_info) > 300 else traceback_info
        
        suggested_actions = [
            "Проверить логи приложения",
            "Связаться с пользователем для уточнения",
            "Проверить состояние внешних сервисов",
            "Обновить FAQ если это частая проблема"
        ]
        
        return await self.send_notification(
            level=AlertLevel.ERROR,
            title="Ошибка у пользователя",
            message="Пользователь столкнулся с ошибкой при использовании бота",
            user_info=user_info,
            error_details=error_details,
            suggested_actions=suggested_actions
        )
    
    async def notify_n8n_timeout(self,
                                webhook_type: str,
                                user_info: Dict[str, Any],
                                timeout_duration: int,
                                request_data: Optional[Dict[str, Any]] = None) -> bool:
        """Уведомление о таймауте N8N"""
        
        error_details = {
            "Тип вебхука": webhook_type,
            "Таймаут (сек)": str(timeout_duration),
            "URL": self._get_webhook_url(webhook_type)
        }
        
        if request_data:
            # Добавляем краткую информацию о запросе
            if webhook_type == "niche":
                error_details["Описание"] = request_data.get('description', 'N/A')[:100]
            elif webhook_type == "topic":
                error_details["Тема"] = request_data.get('topic', 'N/A')[:100]
                error_details["Ниша"] = request_data.get('niche', 'N/A')
            elif webhook_type == "post":
                error_details["Ответ пользователя"] = request_data.get('user_answer', 'N/A')[:100]
        
        suggested_actions = [
            f"Проверить статус N8N сервера",
            f"Проверить производительность {webhook_type} workflow",
            "Увеличить таймаут если нужно",
            "Оптимизировать промпты для ускорения",
            "Проверить нагрузку на OpenAI API"
        ]
        
        return await self.send_notification(
            level=AlertLevel.WARNING,
            title=f"N8N Таймаут: {webhook_type}",
            message=f"N8N не ответил в течение {timeout_duration} секунд",
            user_info=user_info,
            error_details=error_details,
            suggested_actions=suggested_actions
        )
    
    async def notify_n8n_error(self,
                              webhook_type: str,
                              error_code: int,
                              error_message: str,
                              user_info: Dict[str, Any]) -> bool:
        """Уведомление об ошибке N8N"""
        
        error_details = {
            "Тип вебхука": webhook_type,
            "HTTP код": str(error_code),
            "Ошибка": error_message[:200],
            "URL": self._get_webhook_url(webhook_type)
        }
        
        suggested_actions = [
            "Проверить статус N8N сервера",
            "Проверить workflow на ошибки",
            "Проверить доступность OpenAI API",
            "Проверить правильность промптов"
        ]
        
        return await self.send_notification(
            level=AlertLevel.ERROR,
            title=f"N8N Ошибка: {webhook_type}",
            message=f"N8N вернул ошибку {error_code}",
            user_info=user_info,
            error_details=error_details,
            suggested_actions=suggested_actions
        )
    
    async def notify_database_error(self,
                                  operation: str,
                                  error_message: str,
                                  user_info: Optional[Dict[str, Any]] = None) -> bool:
        """Уведомление об ошибке БД"""
        
        error_details = {
            "Операция": operation,
            "Ошибка": error_message[:300]
        }
        
        suggested_actions = [
            "Проверить статус Supabase",
            "Проверить подключение к БД",
            "Проверить правильность SQL запросов",
            "Проверить RLS политики"
        ]
        
        return await self.send_notification(
            level=AlertLevel.CRITICAL,
            title="Ошибка базы данных",
            message="Возникла проблема при работе с базой данных",
            user_info=user_info,
            error_details=error_details,
            suggested_actions=suggested_actions
        )
    
    async def notify_rate_limit(self,
                              service: str,
                              user_info: Dict[str, Any]) -> bool:
        """Уведомление о превышении лимитов"""
        
        error_details = {
            "Сервис": service,
            "Время": datetime.now().strftime('%H:%M:%S')
        }
        
        suggested_actions = [
            f"Проверить лимиты {service}",
            "Реализовать более агрессивное rate limiting",
            "Рассмотреть увеличение лимитов"
        ]
        
        return await self.send_notification(
            level=AlertLevel.WARNING,
            title=f"Rate Limit: {service}",
            message=f"Превышен лимит запросов к {service}",
            user_info=user_info,
            error_details=error_details,
            suggested_actions=suggested_actions
        )
    
    async def notify_system_info(self,
                               title: str,
                               message: str,
                               details: Optional[Dict[str, Any]] = None) -> bool:
        """Информационное уведомление"""
        
        return await self.send_notification(
            level=AlertLevel.INFO,
            title=title,
            message=message,
            error_details=details
        )
    
    def _get_webhook_url(self, webhook_type: str) -> str:
        """Получает URL вебхука по типу"""
        from config import N8N_NICHE_WEBHOOK_URL, N8N_TOPIC_WEBHOOK_URL, N8N_POST_WEBHOOK_URL
        
        urls = {
            "niche": N8N_NICHE_WEBHOOK_URL or "Не настроен",
            "topic": N8N_TOPIC_WEBHOOK_URL or "Не настроен",
            "post": N8N_POST_WEBHOOK_URL or "Не настроен"
        }
        
        return urls.get(webhook_type, "Unknown")

# Глобальный экземпляр для использования в других модулях
admin_notifier = AdminNotifier()

# Вспомогательные функции для быстрого доступа
async def notify_user_error(error_type: str, error_message: str, user_info: Dict[str, Any], traceback_info: Optional[str] = None):
    """Быстрое уведомление об ошибке пользователя"""
    return await admin_notifier.notify_user_error(error_type, error_message, user_info, traceback_info)

async def notify_n8n_timeout(webhook_type: str, user_info: Dict[str, Any], timeout_duration: int, request_data: Optional[Dict[str, Any]] = None):
    """Быстрое уведомление о таймауте N8N"""
    return await admin_notifier.notify_n8n_timeout(webhook_type, user_info, timeout_duration, request_data)

async def notify_n8n_error(webhook_type: str, error_code: int, error_message: str, user_info: Dict[str, Any]):
    """Быстрое уведомление об ошибке N8N"""
    return await admin_notifier.notify_n8n_error(webhook_type, error_code, error_message, user_info)

async def notify_database_error(operation: str, error_message: str, user_info: Optional[Dict[str, Any]] = None):
    """Быстрое уведомление об ошибке БД"""
    return await admin_notifier.notify_database_error(operation, error_message, user_info)

async def notify_system_info(title: str, message: str, details: Optional[Dict[str, Any]] = None):
    """Быстрое информационное уведомление"""
    return await admin_notifier.notify_system_info(title, message, details)
