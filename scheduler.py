# -*- coding: utf-8 -*-
"""
Планировщик для отправки ежедневных напоминаний
"""

import asyncio
import logging
from datetime import datetime, time
from typing import List, Dict
import pytz
from telegram import Bot, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.error import TelegramError

from config import (
    TELEGRAM_BOT_TOKEN,
    REMINDER_TIME_HOUR,
    REMINDER_TIME_MINUTE,
    TIMEZONE
)
from database import db
from utils import retry_helper, text_formatter
import messages

logger = logging.getLogger(__name__)

class ReminderScheduler:
    """Класс для управления ежедневными напоминаниями"""
    
    def __init__(self):
        """Инициализация планировщика"""
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.is_running = False
        self.timezone = pytz.timezone(TIMEZONE)
        self.subscription_manager = None
    
    def set_subscription_manager(self, subscription_manager):
        """Устанавливает менеджер подписок"""
        self.subscription_manager = subscription_manager
    
    async def send_daily_reminders(self, specific_day: int = None):
        """Отправляет ежедневные напоминания всем активным пользователям
        
        Args:
            specific_day (int, optional): Номер дня (1-31) для отправки. 
                                        Если не указан, используется текущий день.
        """
        try:
            if specific_day:
                logger.info(f"Начинаем РУЧНУЮ отправку напоминаний для дня {specific_day}")
                day_of_month = specific_day
            else:
                logger.info("Начинаем АВТОМАТИЧЕСКУЮ отправку ежедневных напоминаний")
                # ВАЖНО: Автоматическая рассылка ВСЕГДА использует реальный текущий день
                from datetime import datetime
                today = datetime.now()
                day_of_month = today.day
                logger.info(f"Используем РЕАЛЬНЫЙ текущий день: {day_of_month}")
            
            # Для дней больше 31 берем последний день
            if day_of_month > 31:
                day_of_month = 31
            elif day_of_month < 1:
                day_of_month = 1
            
            daily_content = await retry_helper.retry_async_operation(
                lambda: db.get_daily_content(day_of_month)
            )
            
            if daily_content and daily_content.get('reminder_message'):
                reminder_template = daily_content['reminder_message']
                logger.info(f"Используем сообщение для дня {day_of_month}")
            else:
                logger.warning(f"Контент для дня {day_of_month} не найден, используем стандартный")
                reminder_template = messages.DAILY_REMINDER
            
            # Получаем список пользователей для напоминаний
            users = await retry_helper.retry_async_operation(
                lambda: db.get_users_for_reminder()
            )
            
            if not users:
                logger.info("Нет пользователей для отправки напоминаний")
                return
            
            successful_sends = 0
            failed_sends = 0
            
            for user in users:
                try:
                    telegram_id = user['telegram_id']
                    niche = user.get('niche', 'Ваша ниша')
                    
                    # Формируем текст напоминания
                    reminder_text = reminder_template.format(
                        niche=text_formatter.escape_html(niche)
                    )
                    
                    # Создаем кнопку "Предложи мне тему"
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton(
                            messages.BUTTON_SUGGEST_TOPIC, 
                            callback_data='suggest_topic'
                        )]
                    ])
                    
                    # Отправляем напоминание с кнопкой
                    await self.bot.send_message(
                        chat_id=telegram_id,
                        text=reminder_text,
                        parse_mode='HTML',
                        reply_markup=keyboard
                    )
                    
                    successful_sends += 1
                    logger.debug(f"Напоминание отправлено пользователю {telegram_id}")
                    
                    # Небольшая задержка между отправками для избежания лимитов
                    await asyncio.sleep(0.1)
                    
                except TelegramError as e:
                    failed_sends += 1
                    if e.message == "Forbidden: bot was blocked by the user":
                        logger.info(f"Пользователь {telegram_id} заблокировал бота")
                        # Можно пометить пользователя как неактивного
                        try:
                            await db.update_user_state(telegram_id, 'blocked')
                        except:
                            pass
                    else:
                        logger.error(f"Ошибка отправки напоминания пользователю {telegram_id}: {e}")
                
                except Exception as e:
                    failed_sends += 1
                    logger.error(f"Неожиданная ошибка при отправке напоминания пользователю {telegram_id}: {e}")
            
            logger.info(f"Отправка напоминаний завершена. Успешно: {successful_sends}, Ошибок: {failed_sends}")
            
        except Exception as e:
            logger.error(f"Критическая ошибка при отправке ежедневных напоминаний: {e}")
    
    async def reset_weekly_counters(self):
        """Обнуляет еженедельные счетчики постов всех пользователей"""
        try:
            logger.info("Запуск обнуления еженедельных счетчиков постов")
            
            # Вызываем SQL функцию для обнуления счетчиков
            response = db.supabase.rpc('reset_weekly_counters').execute()
            
            updated_count = response.data if response.data else 0
            logger.info(f"Обнулено счетчиков у {updated_count} пользователей")
            
        except Exception as e:
            logger.error(f"Ошибка при обнулении еженедельных счетчиков: {e}")
    
    async def schedule_loop(self):
        """Основной цикл планировщика"""
        logger.info("Запуск планировщика напоминаний")
        
        while self.is_running:
            try:
                now = datetime.now(self.timezone)
                target_time = time(REMINDER_TIME_HOUR, REMINDER_TIME_MINUTE)
                
                # Каждый час логируем текущее время для диагностики
                if now.minute == 0:
                    logger.info(f"Планировщик работает. Текущее время: {now.strftime('%H:%M')} (Moscow), цель: {target_time.strftime('%H:%M')}")
                
                # Проверяем, наступило ли время для отправки напоминаний
                if (now.time().hour == target_time.hour and 
                    now.time().minute == target_time.minute):
                    
                    logger.info(f"Время рассылки! Запускаем отправку напоминаний в {now.strftime('%H:%M')}")
                    await self.send_daily_reminders()
                    
                    # Ждем минуту, чтобы не отправлять напоминания несколько раз
                    await asyncio.sleep(60)
                
                # Проверяем, нужно ли обнулить счетчики (понедельник в 00:01)
                elif (now.weekday() == 0 and  # Понедельник
                      now.time().hour == 0 and 
                      now.time().minute == 1):
                    
                    logger.info(f"Понедельник 00:01! Обнуляем счетчики в {now.strftime('%H:%M')}")
                    await self.reset_weekly_counters()
                    await asyncio.sleep(60)  # Ждем минуту
                    
                    # Проверяем подписки в 8:00
                    if current_time.hour == 8 and current_time.minute == 0:
                        if self.subscription_manager:
                            logger.info("Запуск проверки подписок в 8:00")
                            await self.subscription_manager.run_daily_subscription_check()
                else:
                    # Проверяем каждые 30 секунд
                    await asyncio.sleep(30)
            
            except Exception as e:
                logger.error(f"Ошибка в цикле планировщика: {e}")
                await asyncio.sleep(60)  # Ждем минуту перед повтором при ошибке
    
    def start(self):
        """Запуск планировщика"""
        self.is_running = True
        return asyncio.create_task(self.schedule_loop())
    
    def stop(self):
        """Остановка планировщика"""
        self.is_running = False
        logger.info("Планировщик остановлен")

# Создаем глобальный экземпляр планировщика
scheduler = ReminderScheduler()
