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
    DAILY_CONTENT_TABLE, USER_POST_LIMITS_TABLE,
    GENERATED_POSTS_TABLE, WEEKLY_POST_LIMIT
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
                return response.data[0]
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
            user_data = {
                'telegram_id': telegram_id,
                'email': email.lower(),
                'username': username,
                'first_name': first_name,
                'last_name': last_name,
                'registration_date': datetime.utcnow().isoformat(),
                'state': 'waiting_niche_description',
                'is_active': True
            }
            
            response = self.supabase.table(USERS_TABLE).insert(user_data).execute()
            
            if response.data:
                logger.info(f"Пользователь {telegram_id} успешно создан")
                return response.data[0]
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
            response = self.supabase.table(USERS_TABLE).select("telegram_id, niche").eq("is_active", True).eq("state", "registered").execute()
            
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
                return response.data[0]
            else:
                logger.warning(f"Контент для дня {day_of_month} не найден")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при получении контента для дня {day_of_month}: {e}")
            raise

    async def check_user_post_limit(self, telegram_id: int) -> Dict[str, Any]:
        """
        Проверяет лимит постов пользователя на текущую неделю
        
        Args:
            telegram_id (int): Telegram ID пользователя
            
        Returns:
            Dict: Информация о лимитах пользователя
        """
        try:
            # Сначала получаем ID пользователя
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                raise Exception("Пользователь не найден")
            
            user_id = user['id']
            
            # Вызываем функцию проверки лимита
            response = self.supabase.rpc('check_user_post_limit', {'p_user_id': user_id}).execute()
            
            if response.data:
                result = response.data[0]
                logger.info(f"Лимит пользователя {telegram_id}: {result}")
                return result
            else:
                # Если функции нет, создаем запись вручную
                return {
                    'can_generate': True,
                    'remaining_posts': WEEKLY_POST_LIMIT,
                    'posts_generated': 0,
                    'posts_limit': WEEKLY_POST_LIMIT
                }
                
        except Exception as e:
            logger.error(f"Ошибка при проверке лимита постов пользователя {telegram_id}: {e}")
            raise

    async def increment_user_post_count(self, telegram_id: int) -> bool:
        """
        Увеличивает счетчик постов пользователя
        
        Args:
            telegram_id (int): Telegram ID пользователя
            
        Returns:
            bool: True если успешно, False если лимит превышен
        """
        try:
            # Получаем ID пользователя
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                raise Exception("Пользователь не найден")
            
            user_id = user['id']
            
            # Вызываем функцию инкремента
            response = self.supabase.rpc('increment_user_post_count', {'p_user_id': user_id}).execute()
            
            if response.data:
                result = response.data[0]
                logger.info(f"Счетчик постов пользователя {telegram_id} обновлен: {result}")
                return result
            else:
                logger.warning(f"Не удалось обновить счетчик постов пользователя {telegram_id}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при обновлении счетчика постов пользователя {telegram_id}: {e}")
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
        try:
            # Получаем ID пользователя
            user = await self.get_user_by_telegram_id(telegram_id)
            if not user:
                raise Exception("Пользователь не найден")
            
            user_id = user['id']
            
            # Получаем начало недели
            from datetime import datetime, timedelta
            today = datetime.now().date()
            week_start = today - timedelta(days=today.weekday())
            
            post_data = {
                'user_id': user_id,
                'daily_content_id': content_data.get('id') if content_data else None,
                'adapted_topic': adapted_topic,
                'user_question': question,
                'user_answer': user_answer,
                'generated_content': generated_content,
                'week_start_date': week_start.isoformat()
            }
            
            response = self.supabase.table(GENERATED_POSTS_TABLE).insert(post_data).execute()
            
            if response.data:
                logger.info(f"Пост пользователя {telegram_id} сохранен в историю")
                return True
            else:
                logger.warning(f"Не удалось сохранить пост пользователя {telegram_id}")
                return False
                
        except Exception as e:
            logger.error(f"Ошибка при сохранении поста пользователя {telegram_id}: {e}")
            raise

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
            
            # Получаем начало недели
            from datetime import datetime, timedelta
            today = datetime.now().date()
            week_start = today - timedelta(days=today.weekday())
            
            response = self.supabase.table(GENERATED_POSTS_TABLE).select("*").eq("user_id", user_id).eq("week_start_date", week_start.isoformat()).order("created_at", desc=True).execute()
            
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
