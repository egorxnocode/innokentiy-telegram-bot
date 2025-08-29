# -*- coding: utf-8 -*-
"""
Расширенная обработка ошибок для Telegram бота
"""

import logging
import traceback
from functools import wraps
from typing import Callable, Any
from telegram import Update
from telegram.ext import ContextTypes
from telegram.error import (
    TelegramError, 
    BadRequest, 
    Forbidden, 
    NetworkError, 
    TimedOut,
    RetryAfter
)
import asyncio

from admin_notifier import notify_user_error, notify_system_info

from database import db
import messages

logger = logging.getLogger(__name__)

class BotErrorHandler:
    """Класс для централизованной обработки ошибок"""
    
    @staticmethod
    async def handle_telegram_error(update: Update, context: ContextTypes.DEFAULT_TYPE, error: TelegramError):
        """Обработка ошибок Telegram API"""
        
        error_message = messages.ERROR_GENERAL
        log_message = f"Telegram error: {error}"
        
        if isinstance(error, BadRequest):
            if "message is not modified" in str(error):
                # Игнорируем эту ошибку - сообщение уже в нужном состоянии
                return
            elif "message to edit not found" in str(error):
                log_message = f"Сообщение для редактирования не найдено: {error}"
                return
            elif "chat not found" in str(error):
                log_message = f"Чат не найден: {error}"
                return
            else:
                error_message = "Некорректный запрос. Попробуйте еще раз."
        
        elif isinstance(error, Forbidden):
            if "bot was blocked by the user" in str(error):
                # Пользователь заблокировал бота
                if update and update.effective_user:
                    try:
                        await db.update_user_state(update.effective_user.id, 'blocked')
                        logger.info(f"Пользователь {update.effective_user.id} заблокировал бота")
                    except Exception as e:
                        logger.error(f"Ошибка обновления статуса заблокированного пользователя: {e}")
                return
            else:
                error_message = "Нет доступа для выполнения этого действия."
        
        elif isinstance(error, NetworkError):
            error_message = "Проблемы с сетью. Попробуйте позже."
            log_message = f"Network error: {error}"
        
        elif isinstance(error, TimedOut):
            error_message = "Превышено время ожидания. Попробуйте еще раз."
            log_message = f"Timeout error: {error}"
        
        elif isinstance(error, RetryAfter):
            retry_after = error.retry_after
            error_message = f"Слишком много запросов. Попробуйте через {retry_after} секунд."
            log_message = f"Rate limit exceeded, retry after {retry_after} seconds"
            
        logger.error(log_message)
        
        # Отправляем уведомление админу
        if update and update.effective_user:
            user_info = {
                'telegram_id': update.effective_user.id,
                'first_name': update.effective_user.first_name,
                'username': update.effective_user.username,
                'niche': 'N/A',
                'state': 'N/A'
            }
            
            # Пытаемся получить дополнительную информацию из БД
            try:
                user_data = await db.get_user_by_telegram_id(update.effective_user.id)
                if user_data:
                    user_info['niche'] = user_data.get('niche', 'N/A')
                    user_info['state'] = user_data.get('state', 'N/A')
            except:
                pass  # Не критично если не удалось получить данные
            
            # Отправляем уведомление админу (без await чтобы не блокировать)
            asyncio.create_task(notify_user_error(
                error_type=type(error).__name__,
                error_message=str(error),
                user_info=user_info,
                traceback_info=traceback.format_exc()
            ))
        
        # Отправляем сообщение пользователю, если возможно
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    error_message,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение об ошибке: {e}")
    
    @staticmethod
    async def handle_database_error(update: Update, context: ContextTypes.DEFAULT_TYPE, error: Exception):
        """Обработка ошибок базы данных"""
        
        logger.error(f"Database error: {error}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    messages.ERROR_DATABASE,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение об ошибке БД: {e}")
    
    @staticmethod
    async def handle_general_error(update: Update, context: ContextTypes.DEFAULT_TYPE, error: Exception):
        """Обработка общих ошибок"""
        
        logger.error(f"General error: {error}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        logger.debug(f"Update type: {type(update)}, has effective_message: {hasattr(update, 'effective_message') if update else 'update is None'}")
        
        # Проверяем, что update является правильным объектом Update
        if update and hasattr(update, 'effective_message') and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    messages.ERROR_GENERAL,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Не удалось отправить сообщение об общей ошибке: {e}")

def telegram_error_handler(func: Callable) -> Callable:
    """Декоратор для обработки ошибок в обработчиках Telegram"""
    
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs) -> Any:
        try:
            return await func(update, context, *args, **kwargs)
        
        except TelegramError as e:
            await BotErrorHandler.handle_telegram_error(update, context, e)
        
        except Exception as e:
            # Проверяем, связана ли ошибка с базой данных
            if any(keyword in str(e).lower() for keyword in ['supabase', 'database', 'connection', 'sql']):
                await BotErrorHandler.handle_database_error(update, context, e)
            else:
                await BotErrorHandler.handle_general_error(update, context, e)
    
    return wrapper

def database_error_handler(func: Callable) -> Callable:
    """Декоратор для обработки ошибок базы данных"""
    
    @wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await func(*args, **kwargs)
        
        except Exception as e:
            logger.error(f"Database operation failed: {func.__name__}")
            logger.error(f"Error: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    return wrapper

class RateLimiter:
    """Класс для ограничения частоты запросов"""
    
    def __init__(self, max_calls: int = 30, time_window: int = 60):
        """
        Args:
            max_calls: Максимальное количество вызовов
            time_window: Временное окно в секундах
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = {}
    
    async def is_allowed(self, user_id: int) -> bool:
        """Проверяет, разрешен ли запрос для пользователя"""
        
        current_time = asyncio.get_event_loop().time()
        
        if user_id not in self.calls:
            self.calls[user_id] = []
        
        # Удаляем старые запросы
        self.calls[user_id] = [
            call_time for call_time in self.calls[user_id]
            if current_time - call_time < self.time_window
        ]
        
        # Проверяем лимит
        if len(self.calls[user_id]) >= self.max_calls:
            return False
        
        # Добавляем текущий запрос
        self.calls[user_id].append(current_time)
        return True

def rate_limit_handler(rate_limiter: RateLimiter):
    """Декоратор для ограничения частоты запросов"""
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs) -> Any:
            # Проверяем, что update действительно является объектом Update
            if not hasattr(update, 'effective_user') or not update.effective_user:
                logger.warning(f"Rate limiter: Invalid update object type: {type(update)}")
                return await func(update, context, *args, **kwargs)
            
            user_id = update.effective_user.id
            
            if not await rate_limiter.is_allowed(user_id):
                logger.warning(f"Rate limit exceeded for user {user_id}")
                await update.message.reply_text(
                    "<b>⚠️ Слишком много запросов</b>\n\n"
                    "Пожалуйста, подождите немного перед следующим запросом.",
                    parse_mode='HTML'
                )
                return
            
            return await func(update, context, *args, **kwargs)
        
        return wrapper
    return decorator

# Создаем глобальный экземпляр rate limiter
global_rate_limiter = RateLimiter(max_calls=30, time_window=60)

class ValidationError(Exception):
    """Исключение для ошибок валидации"""
    pass

class DatabaseConnectionError(Exception):
    """Исключение для ошибок подключения к базе данных"""
    pass

class ExternalServiceError(Exception):
    """Исключение для ошибок внешних сервисов (N8N, OpenAI)"""
    pass
