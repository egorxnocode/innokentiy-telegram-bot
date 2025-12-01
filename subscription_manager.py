# -*- coding: utf-8 -*-
"""
Модуль для управления подписками пользователей
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any
from database import Database
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
import messages

logger = logging.getLogger(__name__)

class SubscriptionManager:
    def __init__(self, bot: Bot, database: Database):
        self.bot = bot
        self.db = database
        self.payment_url = "https://example.com/payment"  # Заменить на реальную ссылку
    
    def set_payment_url(self, url: str):
        """Устанавливает ссылку для оплаты подписки"""
        self.payment_url = url
        logger.info(f"Ссылка для оплаты обновлена: {url}")
    
    async def check_expiring_subscriptions(self):
        """Проверяет подписки, истекающие через 7 и 1 день"""
        try:
            logger.info("Начинаем проверку истекающих подписок")
            
            # Проверяем подписки, истекающие через 7 дней
            users_7_days = await self.db.get_users_with_expiring_subscriptions(7)
            for user in users_7_days:
                await self._send_expiration_notification(user, 7)
            
            # Проверяем подписки, истекающие через 1 день
            users_1_day = await self.db.get_users_with_expiring_subscriptions(1)
            for user in users_1_day:
                await self._send_expiration_notification(user, 1)
            
            logger.info(f"Проверка завершена. Уведомлений за 7 дней: {len(users_7_days)}, за 1 день: {len(users_1_day)}")
            
        except Exception as e:
            logger.error(f"Ошибка при проверке истекающих подписок: {e}")
    
    async def check_expired_subscriptions(self):
        """Проверяет и обрабатывает истекшие подписки"""
        try:
            logger.info("Начинаем проверку истекших подписок")
            
            # Получаем пользователей с истекшими подписками
            expired_users = await self.db.get_users_with_expired_subscriptions()
            
            for user in expired_users:
                telegram_id = user['telegram_id']
                
                # Обновляем статус на inactive
                await self.db.update_subscription_status(telegram_id, 'inactive')
                
                # Отправляем уведомление
                await self._send_expired_notification(user)
            
            logger.info(f"Обработано истекших подписок: {len(expired_users)}")
            
        except Exception as e:
            logger.error(f"Ошибка при проверке истекших подписок: {e}")
    
    async def _send_expiration_notification(self, user: Dict[str, Any], days_left: int):
        """Отправляет уведомление о скором истечении подписки"""
        try:
            telegram_id = user['telegram_id']
            
            # Выбираем текст в зависимости от количества дней
            if days_left == 7:
                message_text = messages.SUBSCRIPTION_EXPIRING_7_DAYS
            elif days_left == 1:
                message_text = messages.SUBSCRIPTION_EXPIRING_1_DAY
            else:
                return  # Неподдерживаемое количество дней
            
            # Создаем кнопку для продления
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    messages.BUTTON_RENEW_SUBSCRIPTION, 
                    url=self.payment_url
                )]
            ])
            
            await self.bot.send_message(
                chat_id=telegram_id,
                text=message_text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
            
            logger.info(f"Отправлено уведомление о истечении через {days_left} дней пользователю {telegram_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления пользователю {user.get('telegram_id')}: {e}")
    
    async def _send_expired_notification(self, user: Dict[str, Any]):
        """Отправляет уведомление об истекшей подписке"""
        try:
            telegram_id = user['telegram_id']
            
            # Создаем кнопку для продления
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    messages.BUTTON_RENEW_SUBSCRIPTION, 
                    url=self.payment_url
                )]
            ])
            
            await self.bot.send_message(
                chat_id=telegram_id,
                text=messages.SUBSCRIPTION_EXPIRED,
                parse_mode='HTML',
                reply_markup=keyboard
            )
            
            logger.info(f"Отправлено уведомление об истекшей подписке пользователю {telegram_id}")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления об истечении пользователю {user.get('telegram_id')}: {e}")
    
    async def check_user_access(self, telegram_id: int) -> Dict[str, Any]:
        """
        Проверяет доступ пользователя к функциям бота
        
        Returns:
            Dict: {'has_access': bool, 'reason': str, 'message': str}
        """
        try:
            subscription_info = await self.db.check_user_subscription_status(telegram_id)
            
            if subscription_info['is_active']:
                return {
                    'has_access': True,
                    'reason': 'active_subscription',
                    'message': None
                }
            else:
                # Создаем кнопку для продления
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(
                        messages.BUTTON_RENEW_SUBSCRIPTION, 
                        url=self.payment_url
                    )]
                ])
                
                return {
                    'has_access': False,
                    'reason': subscription_info['reason'],
                    'message': messages.SUBSCRIPTION_EXPIRED,
                    'keyboard': keyboard
                }
                
        except Exception as e:
            logger.error(f"Ошибка при проверке доступа пользователя {telegram_id}: {e}")
            return {
                'has_access': False,
                'reason': 'error',
                'message': "Произошла ошибка при проверке подписки. Попробуйте позже."
            }
    
    async def send_access_denied_message(self, telegram_id: int):
        """Отправляет сообщение о заблокированном доступе"""
        try:
            access_info = await self.check_user_access(telegram_id)
            
            if not access_info['has_access'] and access_info.get('message'):
                keyboard = access_info.get('keyboard')
                
                await self.bot.send_message(
                    chat_id=telegram_id,
                    text=access_info['message'],
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
                
                logger.info(f"Отправлено сообщение о заблокированном доступе пользователю {telegram_id}")
                
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения о заблокированном доступе пользователю {telegram_id}: {e}")
    
    async def run_daily_subscription_check(self):
        """Запускает ежедневную проверку подписок"""
        try:
            logger.info("Запуск ежедневной проверки подписок")
            
            # Проверяем истекающие подписки
            await self.check_expiring_subscriptions()
            
            # Проверяем истекшие подписки
            await self.check_expired_subscriptions()
            
            logger.info("Ежедневная проверка подписок завершена")
            
        except Exception as e:
            logger.error(f"Ошибка при ежедневной проверке подписок: {e}")
