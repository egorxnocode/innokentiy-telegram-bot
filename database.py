# -*- coding: utf-8 -*-
"""
Модуль для работы с Supabase базой данных
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from supabase import create_client, Client
from config import (
    SUPABASE_URL, SUPABASE_KEY, USERS_TABLE, EMAILS_TABLE,
    DAILY_CONTENT_TABLE, WEEKLY_POST_LIMIT
)

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        """Инициализация подключения к Supabase"""
        try:
            self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
            logger.info("Подключение к Supabase установлено")
        except Exception as e:
            logger.error(f"Ошибка подключения к Supabase: {e}")
            raise

    async def check_email_exists(self, email: str) -> bool:
        """
        Проверяет существование email в таблице разрешенных email'ов
        
        Args:
            email (str): Email адрес для проверки
            
        Returns:
            bool: True если email найден, False если не найден
        """
        try:
            response = self.supabase.table(EMAILS_TABLE).select("email").eq("email", email.lower()).execute()
            
            if response.data:
                logger.info(f"Email {email} найден в базе данных")
                return True
            else:
                logger.info(f"Email {email} не найден в базе данных")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при проверке email {email}: {e}")
            raise

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """
        Получает пользователя по Telegram ID
        
        Args:
            telegram_id (int): Telegram ID пользователя
            
        Returns:
            Optional[Dict]: Данные пользователя или None если не найден
        """
        try:
            response = self.supabase.table(USERS_TABLE).select("*").eq("telegram_id", telegram_id).execute()
            
            if response.data:
                logger.info(f"Пользователь с Telegram ID {telegram_id} найден")
                # Безопасное получение первого элемента
                if isinstance(response.data, list) and len(response.data) > 0:
                    return response.data[0]
                else:
                    return response.data
            else:
                logger.info(f"Пользователь с Telegram ID {telegram_id} не найден")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при получении пользователя {telegram_id}: {e}")
            raise

    async def create_user(self, telegram_id: int, email: str, username: str = None, first_name: str = None, last_name: str = None) -> Dict[str, Any]:
        """
        Создает нового пользователя
        
        Args:
            telegram_id (int): Telegram ID пользователя
            email (str): Email адрес пользователя
            username (str, optional): Username пользователя в Telegram
            first_name (str, optional): Имя пользователя
            last_name (str, optional): Фамилия пользователя
            
        Returns:
            Dict: Созданная запись пользователя
        """
        try:
            # Устанавливаем дату окончания подписки на 01.02.2026
            subscription_end = datetime(2026, 2, 1).isoformat()
            
            user_data = {
                'telegram_id': telegram_id,
                'email': email.lower(),
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'registration_date': datetime.utcnow().isoformat(),
                'state': 'waiting_niche_description',
                'is_active': True,
                'subscription_end_date': subscription_end
            }
            
            response = self.supabase.table(USERS_TABLE).insert(user_data).execute()
            
            if response.data:
                logger.info(f"Пользователь {telegram_id} успешно создан")
                # Безопасное получение первого элемента
                if isinstance(response.data, list) and len(response.data) > 0:
                    return response.data[0]
                else:
                    return response.data
            else:
                raise Exception("Не удалось создать пользователя")
                
        except Exception as e:
            logger.error(f"Ошибка при создании пользователя {telegram_id}: {e}")
            raise

    async def update_user_state(self, telegram_id: int, state: str) -> bool:
        """
        Обновляет состояние пользователя
        
        Args:
            telegram_id (int): Telegram ID пользователя
            state (str): Новое состояние пользователя
            
        Returns:
            bool: True если обновление успешно
        """
        try:
            response = self.supabase.table(USERS_TABLE).update({
                'state': state,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('telegram_id', telegram_id).execute()
            
            if response.data:
                logger.info(f"Состояние пользователя {telegram_id} обновлено на {state}")
                return True
            else:
                logger.warning(f"Не удалось обновить состояние пользователя {telegram_id}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении состояния пользователя {telegram_id}: {e}")
            raise

    async def update_user_niche(self, telegram_id: int, niche: str) -> bool:
        """
        Обновляет нишу пользователя
        
        Args:
            telegram_id (int): Telegram ID пользователя
            niche (str): Ниша пользователя
            
        Returns:
            bool: True если обновление успешно
        """
        try:
            response = self.supabase.table(USERS_TABLE).update({
                'niche': niche,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('telegram_id', telegram_id).execute()
            
            if response.data:
                logger.info(f"Ниша пользователя {telegram_id} обновлена: {niche}")
                return True
            else:
                logger.warning(f"Не удалось обновить нишу пользователя {telegram_id}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении ниши пользователя {telegram_id}: {e}")
            raise

    async def get_users_count(self) -> int:
        """
        Получает количество зарегистрированных пользователей
        
        Returns:
            int: Количество пользователей
        """
        try:
            response = self.supabase.table(USERS_TABLE).select("telegram_id", count="exact").execute()
            count = response.count if response.count is not None else 0
            logger.info(f"Всего пользователей в базе: {count}")
            return count
            
        except Exception as e:
            logger.error(f"Ошибка при получении количества пользователей: {e}")
            raise

    async def get_users_for_reminder(self) -> list:
        """
        Получает список пользователей для отправки напоминаний
        
        Returns:
            list: Список пользователей с их данными
        """
        try:
            # Получаем всех пользователей которые завершили регистрацию
            # Исключаем только состояния незавершенной регистрации
            incomplete_states = ["waiting_email", "email_verified", "waiting_niche_description", "waiting_niche_confirmation", "niche_confirmed"]
            response = self.supabase.table(USERS_TABLE).select("telegram_id, niche").eq("is_active", True).not_.in_("state", incomplete_states).execute()
            
            if response.data:
                logger.info(f"Найдено {len(response.data)} пользователей для напоминаний")
                return response.data
            else:
                logger.info("Нет пользователей для напоминаний")
                return []
                
        except Exception as e:
            logger.error(f"Ошибка при получении пользователей для напоминаний: {e}")
            raise

    async def get_daily_content(self, day_of_month: int) -> Optional[Dict[str, Any]]:
        """
        Получает ежедневный контент из базы данных (сообщение + тема + вопрос)
        
        Args:
            day_of_month (int): День месяца (1-31)
            
        Returns:
            Optional[Dict]: Данные контента или None
        """
        try:
            response = self.supabase.table(DAILY_CONTENT_TABLE).select("*").eq("day_of_month", day_of_month).eq("is_active", True).execute()
            
            if response.data:
                logger.info(f"Контент для дня {day_of_month} найден")
                # Безопасное получение первого элемента
                if isinstance(response.data, list) and len(response.data) > 0:
                    return response.data[0]
                else:
                    return response.data
            else:
                logger.warning(f"Контент для дня {day_of_month} не найден")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при получении контента для дня {day_of_month}: {e}")
            raise

    async def get_active_reminder_day(self) -> Optional[int]:
        """
        Получает активный день рассылки из файла настроек
        
        Returns:
            Optional[int]: День месяца (1-31) или None если не установлен
        """
        try:
            import os
            reminder_day_file = "/tmp/active_reminder_day.txt"
            
            if os.path.exists(reminder_day_file):
                with open(reminder_day_file, 'r') as f:
                    day_str = f.read().strip()
                    if day_str.isdigit():
                        day = int(day_str)
                        if 1 <= day <= 31:
                            logger.info(f"Загружен активный день рассылки: {day}")
                            return day
            
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении активного дня рассылки: {e}")
            return None

    async def set_active_reminder_day(self, day_of_month: int) -> bool:
        """
        Устанавливает активный день рассылки в файл
        
        Args:
            day_of_month (int): День месяца (1-31)
            
        Returns:
            bool: Успешность операции
        """
        try:
            import os
            reminder_day_file = "/tmp/active_reminder_day.txt"
            
            # Валидация
            if not (1 <= day_of_month <= 31):
                logger.error(f"Неверный день месяца: {day_of_month}")
                return False
            
            # Сохраняем в файл
            with open(reminder_day_file, 'w') as f:
                f.write(str(day_of_month))
            
            logger.info(f"Сохранен активный день рассылки: {day_of_month}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при установке активного дня рассылки: {e}")
            return False

    async def clear_active_reminder_day(self) -> bool:
        """
        Очищает активный день рассылки (возвращает к использованию текущего дня)
        
        Returns:
            bool: Успешность операции
        """
        try:
            import os
            reminder_day_file = "/tmp/active_reminder_day.txt"
            
            if os.path.exists(reminder_day_file):
                os.remove(reminder_day_file)
                logger.info("Тестовый день очищен, возвращаемся к текущему дню")
            
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при очистке активного дня: {e}")
            return False

    async def check_user_post_limit(self, telegram_id: int) -> Dict[str, Any]:
        """
        Проверяет лимит постов пользователя используя счетчик в таблице users
        
        Args:
            telegram_id (int): Telegram ID пользователя
            
        Returns:
            Dict: Информация о лимитах пользователя
        """
        try:
            # Получаем пользователя с счетчиком постов
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                raise Exception("Пользователь не найден")
            
            # Обнуляем счетчики если нужно (вызываем SQL функцию)
            self.supabase.rpc('reset_weekly_counters').execute()
            
            # Получаем обновленного пользователя
            user = await self.get_user_by_telegram_id(telegram_id)
            
            posts_count = user.get('weekly_posts_count', 0)
            remaining_posts = max(0, WEEKLY_POST_LIMIT - posts_count)
            can_generate = posts_count < WEEKLY_POST_LIMIT
            
            result = {
                'can_generate': can_generate,
                'remaining_posts': remaining_posts,
                'posts_generated': posts_count,
                'posts_limit': WEEKLY_POST_LIMIT
            }
            
            logger.info(f"Лимит пользователя {telegram_id}: {result}")
            return result
                
        except Exception as e:
            logger.error(f"Ошибка при проверке лимита постов пользователя {telegram_id}: {e}")
            raise

    async def save_user_post(self, telegram_id: int, post_content: str, adapted_topic: str = "", 
                           user_question: str = "", user_answer: str = "") -> bool:
        """
        Сохраняет пост пользователя и увеличивает счетчик
        
        Args:
            telegram_id (int): Telegram ID пользователя
            post_content (str): Содержимое поста
            adapted_topic (str): Адаптированная тема
            user_question (str): Вопрос пользователю
            user_answer (str): Ответ пользователя
            
        Returns:
            bool: True если успешно сохранено
        """
        try:
            # Получаем ID пользователя
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                raise Exception("Пользователь не найден")
            
            user_id = user['id']
            
            # Сохраняем пост в таблицу user_posts
            response = self.supabase.table('user_posts').insert({
                'user_id': user_id,
                'post_content': post_content,
                'adapted_topic': adapted_topic,
                'user_question': user_question,
                'user_answer': user_answer
            }).execute()
            
            if response.data:
                # Увеличиваем счетчик постов у пользователя
                counter_response = self.supabase.rpc('increment_weekly_post_counter', {'p_user_id': user_id}).execute()
                
                new_count = counter_response.data if counter_response.data else 0
                logger.info(f"Пост пользователя {telegram_id} сохранен. Новый счетчик: {new_count}")
                return True
            else:
                logger.warning(f"Не удалось сохранить пост пользователя {telegram_id}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при сохранении поста пользователя {telegram_id}: {e}")
            raise

    async def save_generated_post(self, telegram_id: int, content_data: Dict[str, Any], 
                                 adapted_topic: str, question: str, user_answer: str, 
                                 generated_content: str) -> bool:
        """
        Сохраняет сгенерированный пост в историю
        
        Args:
            telegram_id (int): Telegram ID пользователя
            content_data (Dict): Данные ежедневного контента
            adapted_topic (str): Адаптированная тема
            question (str): Заданный вопрос
            user_answer (str): Ответ пользователя
            generated_content (str): Сгенерированный контент
            
        Returns:
            bool: True если успешно сохранено
        """
        # Используем новую простую систему
        return await self.save_user_post(
            telegram_id=telegram_id,
            post_content=generated_content,
            adapted_topic=adapted_topic,
            user_question=question,
            user_answer=user_answer
        )

    async def get_user_posts_this_week(self, telegram_id: int) -> list:
        """
        Получает посты пользователя за текущую неделю
        
        Args:
            telegram_id (int): Telegram ID пользователя
            
        Returns:
            list: Список постов пользователя
        """
        try:
            # Получаем ID пользователя
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                return []
            
            user_id = user['id']
            
            # Получаем посты за последние 7 дней
            from datetime import datetime, timedelta
            seven_days_ago = (datetime.now() - timedelta(days=7)).isoformat()
            
            response = self.supabase.table('user_posts').select("*").eq("user_id", user_id).gte("created_at", seven_days_ago).order("created_at", desc=True).execute()
            
            if response.data:
                logger.info(f"Найдено {len(response.data)} постов пользователя {telegram_id} за неделю")
                return response.data
            else:
                return []
                
        except Exception as e:
            logger.error(f"Ошибка при получении постов пользователя {telegram_id}: {e}")
            raise

# Создаем глобальный экземпляр базы данных
db = Database()
