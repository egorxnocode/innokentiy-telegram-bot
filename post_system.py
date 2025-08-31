# -*- coding: utf-8 -*-
"""
Система генерации постов для Telegram бота
"""

import logging
import asyncio
import requests
from typing import Optional, Dict, Any, Tuple
from datetime import datetime

from config import (
    N8N_TOPIC_WEBHOOK_URL, N8N_POST_WEBHOOK_URL,
    N8N_TOPIC_TIMEOUT, N8N_POST_TIMEOUT, N8N_CONNECTION_TIMEOUT
)
from database import db
from utils import retry_helper, text_formatter
import messages
from admin_notifier import notify_n8n_timeout, notify_n8n_error

logger = logging.getLogger(__name__)

class N8NTimeoutError(Exception):
    """Исключение для таймаутов N8N"""
    pass

class N8NConnectionError(Exception):
    """Исключение для ошибок подключения к N8N"""
    pass

class PostSystem:
    """Класс для управления системой генерации постов"""
    
    @staticmethod
    async def _get_user_info_for_notification(telegram_id: int, niche: str) -> Dict[str, Any]:
        """Получает информацию о пользователе для уведомлений"""
        user_info = {
            'telegram_id': telegram_id,
            'first_name': 'N/A',
            'username': 'N/A', 
            'niche': niche,
            'state': 'N/A'
        }
        
        try:
            user_data = await db.get_user_by_telegram_id(telegram_id)
            if user_data:
                user_info.update({
                    'first_name': user_data.get('first_name', 'N/A'),
                    'username': user_data.get('username', 'N/A'),
                    'state': user_data.get('state', 'N/A')
                })
        except Exception as e:
            logger.warning(f"Не удалось получить данные пользователя {telegram_id}: {e}")
        
        return user_info
    
    @staticmethod
    async def get_content_for_today() -> Optional[Dict[str, Any]]:
        """
        Получает контент для текущего активного дня (сообщение + тема + вопрос)
        
        Returns:
            Optional[Dict]: Данные контента или None
        """
        try:
            # Получаем активный день рассылки
            day_of_month = await PostSystem.get_current_reminder_day()
            
            content_data = await retry_helper.retry_async_operation(
                lambda: db.get_daily_content(day_of_month)
            )
            
            return content_data
            
        except Exception as e:
            logger.error(f"Ошибка при получении контента дня: {e}")
            return None
    
    @staticmethod
    async def get_current_reminder_day() -> int:
        """
        Получает день для генерации контента (темы)
        Используется только для предложения тем пользователям, НЕ для автоматической рассылки
        
        Returns:
            int: День месяца (1-31)
        """
        try:
            # Проверяем, есть ли сохраненный тестовый день (установленный админской командой)
            saved_day = await db.get_active_reminder_day()
            if saved_day:
                logger.info(f"Используем тестовый день для генерации тем: {saved_day}")
                return saved_day
            
            # Если нет тестового дня, используем текущий календарный день
            today = datetime.now()
            day_of_month = today.day
            
            # Для дней больше 31 берем последний день
            if day_of_month > 31:
                day_of_month = 31
            elif day_of_month < 1:
                day_of_month = 1
                
            return day_of_month
            
        except Exception as e:
            logger.error(f"Ошибка при получении дня для тем: {e}")
            # В случае ошибки возвращаем текущий день
            today = datetime.now()
            return max(1, min(31, today.day))
    
    @staticmethod
    def get_actual_current_day() -> int:
        """
        Получает РЕАЛЬНЫЙ текущий день для автоматической рассылки
        Эта функция ВСЕГДА возвращает текущий календарный день
        
        Returns:
            int: Текущий день месяца (1-31)
        """
        try:
            today = datetime.now()
            day_of_month = today.day
            
            # Для дней больше 31 берем последний день
            if day_of_month > 31:
                day_of_month = 31
            elif day_of_month < 1:
                day_of_month = 1
                
            return day_of_month
            
        except Exception as e:
            logger.error(f"Ошибка при получении текущего дня: {e}")
            return 1  # Безопасное значение по умолчанию
    
    @staticmethod
    def _clean_html_for_telegram(content: str) -> str:
        """
        Очищает HTML от неподдерживаемых Telegram тегов
        Telegram поддерживает только: <b>, <i>, <u>, <s>, <code>, <pre>, <a>
        """
        import re
        
        # Заменяем неподдерживаемые теги на поддерживаемые
        content = re.sub(r'<p>', '', content)
        content = re.sub(r'</p>', '\n\n', content)
        content = re.sub(r'<strong>', '<b>', content)
        content = re.sub(r'</strong>', '</b>', content)
        content = re.sub(r'<em>', '<i>', content)
        content = re.sub(r'</em>', '</i>', content)
        
        # Удаляем другие неподдерживаемые теги, оставляя текст
        content = re.sub(r'</?(?:div|span|h[1-6]|ul|ol|li|br)[^>]*>', '', content)
        
        # Убираем лишние переносы строк
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = content.strip()
        
        return content
    
    @staticmethod
    async def adapt_topic_for_niche(topic: str, niche: str) -> Optional[str]:
        """
        Адаптирует универсальную тему под нишу пользователя через N8N
        
        Args:
            topic (str): Универсальная тема
            niche (str): Ниша пользователя
            
        Returns:
            Optional[str]: Адаптированная тема
            
        Raises:
            N8NTimeoutError: При превышении таймаута
            N8NConnectionError: При ошибках подключения
        """
        try:
            from webhook_server import callback_manager
            
            payload = {
                'action': 'adapt_topic',
                'topic': topic,
                'niche': niche,
                'language': 'ru'
            }
            
            logger.info(f"Отправляем асинхронный запрос адаптации темы в N8N")
            
            # Отправляем асинхронный запрос в N8N
            request_id = await callback_manager.send_async_request(
                N8N_TOPIC_WEBHOOK_URL,
                payload,
                "topic"
            )
            
            # Ждем callback от N8N
            logger.info(f"Ожидаю callback от N8N для адаптации темы: {request_id}")
            result = await callback_manager.wait_for_callback(request_id, timeout=180)
            
            if result and result.get('success'):
                adapted_topic = result.get('adapted_topic', '').strip()
                if adapted_topic:
                    logger.info(f"Тема успешно адаптирована: {adapted_topic}")
                    return adapted_topic
                else:
                    logger.warning("N8N вернул пустую адаптированную тему через callback")
                    return None
            else:
                logger.error("Не получен callback от N8N для адаптации темы")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при адаптации темы: {e}")
            return None
    
    @staticmethod
    async def generate_post_content(niche: str, topic: str, question: str, user_answer: str, post_goal: str = "чтобы пост вызвал у человека эмоцию и желание поставить реакцию (сердце, огонь и так далее)") -> Optional[str]:
        """
        Генерирует контент поста на основе ответа пользователя через N8N
        
        Args:
            niche (str): Ниша пользователя
            topic (str): Тема поста
            question (str): Заданный вопрос
            user_answer (str): Ответ пользователя
            post_goal (str): Описание цели поста (подробное описание того, какую реакцию должен вызвать пост)
            
        Returns:
            Optional[str]: Сгенерированный пост
            
        Raises:
            N8NTimeoutError: При превышении таймаута
            N8NConnectionError: При ошибках подключения
        """
        try:
            from webhook_server import callback_manager
            
            payload = {
                'action': 'generate_post',
                'niche': niche,
                'topic': topic,
                'question': question,
                'user_answer': user_answer,
                'post_goal': post_goal,
                'language': 'ru'
            }
            
            logger.info(f"Отправляем асинхронный запрос генерации поста в N8N")
            
            # Отправляем асинхронный запрос в N8N
            request_id = await callback_manager.send_async_request(
                N8N_POST_WEBHOOK_URL,
                payload,
                "post"
            )
            
            # Ждем callback от N8N
            logger.info(f"Ожидаю callback от N8N для генерации поста: {request_id}")
            result = await callback_manager.wait_for_callback(request_id, timeout=180)
            
            if result and result.get('success'):
                generated_content = result.get('generated_post', '').strip()
                if generated_content:
                    logger.info(f"Пост успешно сгенерирован: {len(generated_content)} символов")
                    return generated_content
                else:
                    logger.warning("N8N вернул пустой сгенерированный пост через callback")
                    return None
            else:
                logger.error("Не получен callback от N8N для генерации поста")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка при генерации поста: {e}")
            return None
    
    @staticmethod
    def validate_user_answer(answer: str) -> Tuple[bool, str]:
        """
        Валидирует ответ пользователя
        
        Args:
            answer (str): Ответ пользователя
            
        Returns:
            Tuple[bool, str]: (is_valid, error_message)
        """
        if not answer or not answer.strip():
            return False, "Ответ не может быть пустым"
        
        # Подсчитываем количество слов для других проверок
        words = answer.strip().split()
        # Убрано ограничение на минимальное количество слов
        
        # Проверяем на спам/однообразный текст
        unique_words = set(word.lower() for word in words)
        if len(unique_words) < len(words) * 0.5:  # Меньше 50% уникальных слов
            return False, "Ответ содержит слишком много повторяющихся слов"
        
        return True, ""
    
    @staticmethod
    async def process_topic_request(telegram_id: int, niche: str) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Обрабатывает запрос на предложение темы
        
        Args:
            telegram_id (int): ID пользователя
            niche (str): Ниша пользователя
            
        Returns:
            Tuple[bool, str, Optional[Dict]]: (success, message, topic_data)
        """
        try:
            # Проверяем лимит постов
            limit_info = await retry_helper.retry_async_operation(
                lambda: db.check_user_post_limit(telegram_id)
            )
            
            if not limit_info.get('can_generate', False):
                return False, messages.WEEKLY_LIMIT_EXCEEDED.format(
                    posts_generated=limit_info.get('posts_generated', 0),
                    posts_limit=limit_info.get('posts_limit', 10)
                ), None
            
            # Получаем контент дня
            content_data = await PostSystem.get_content_for_today()
            if not content_data:
                return False, messages.ERROR_NO_TOPICS_AVAILABLE, None
            
            # Адаптируем тему под нишу
            try:
                adapted_topic = await PostSystem.adapt_topic_for_niche(
                    content_data['topic'], 
                    niche
                )
            except N8NTimeoutError:
                # Получаем информацию о пользователе для уведомления
                user_info = await PostSystem._get_user_info_for_notification(telegram_id, niche)
                # Отправляем уведомление админу (без await)
                asyncio.create_task(notify_n8n_timeout(
                    webhook_type="topic",
                    user_info=user_info,
                    timeout_duration=N8N_TOPIC_TIMEOUT,
                    request_data={'topic': content_data['topic'], 'niche': niche}
                ))
                return False, messages.ERROR_TOPIC_TIMEOUT, None
            except N8NConnectionError:
                user_info = await PostSystem._get_user_info_for_notification(telegram_id, niche)
                asyncio.create_task(notify_n8n_error(
                    webhook_type="topic",
                    error_code=500,
                    error_message="Connection error",
                    user_info=user_info
                ))
                return False, messages.ERROR_TOPIC_ADAPTATION, None
            
            if not adapted_topic:
                return False, messages.ERROR_TOPIC_ADAPTATION, None
            
            # Добавляем адаптированную тему в данные
            content_data['adapted_topic'] = adapted_topic
            
            return True, messages.TOPIC_SUGGESTION.format(
                adapted_topic=text_formatter.escape_html(adapted_topic),
                niche=text_formatter.escape_html(niche)
            ), content_data
            
        except Exception as e:
            logger.error(f"Ошибка при обработке запроса темы для пользователя {telegram_id}: {e}")
            return False, messages.ERROR_GENERAL, None
    
    @staticmethod
    async def process_post_generation(telegram_id: int, niche: str, content_data: Dict[str, Any], 
                                    user_answer: str, post_goal: str = "чтобы пост вызвал у человека эмоцию и желание поставить реакцию (сердце, огонь и так далее)") -> Tuple[bool, str]:
        """
        Обрабатывает генерацию поста
        
        Args:
            telegram_id (int): ID пользователя
            niche (str): Ниша пользователя
            content_data (Dict): Данные контента
            user_answer (str): Ответ пользователя
            post_goal (str): Описание цели поста (подробное описание того, какую реакцию должен вызвать пост)
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Валидируем ответ пользователя
            is_valid, validation_error = PostSystem.validate_user_answer(user_answer)
            if not is_valid:
                return False, messages.ERROR_ANSWER_TOO_SHORT
            
            # Проверяем лимит постов еще раз
            limit_info = await retry_helper.retry_async_operation(
                lambda: db.check_user_post_limit(telegram_id)
            )
            
            if not limit_info.get('can_generate', False):
                return False, messages.WEEKLY_LIMIT_EXCEEDED.format(
                    posts_generated=limit_info.get('posts_generated', 0),
                    posts_limit=limit_info.get('posts_limit', 10)
                )
            
            # Генерируем пост
            try:
                generated_content = await PostSystem.generate_post_content(
                    niche=niche,
                    topic=content_data.get('adapted_topic', content_data.get('topic')),
                    question=content_data.get('question', ''),
                    user_answer=user_answer,
                    post_goal=post_goal
                )
            except N8NTimeoutError:
                # Получаем информацию о пользователе для уведомления
                user_info = await PostSystem._get_user_info_for_notification(telegram_id, niche)
                # Отправляем уведомление админу (без await)
                asyncio.create_task(notify_n8n_timeout(
                    webhook_type="post",
                    user_info=user_info,
                    timeout_duration=N8N_POST_TIMEOUT,
                    request_data={
                        'topic': content_data.get('adapted_topic', content_data.get('topic')),
                        'question': content_data.get('question', ''),
                        'user_answer': user_answer[:100]  # Первые 100 символов
                    }
                ))
                return False, messages.ERROR_POST_TIMEOUT
            except N8NConnectionError:
                user_info = await PostSystem._get_user_info_for_notification(telegram_id, niche)
                asyncio.create_task(notify_n8n_error(
                    webhook_type="post",
                    error_code=500,
                    error_message="Connection error",
                    user_info=user_info
                ))
                return False, messages.ERROR_POST_GENERATION
            
            if not generated_content:
                return False, messages.ERROR_POST_GENERATION
            
            # Очищаем HTML от неподдерживаемых тегов
            generated_content = PostSystem._clean_html_for_telegram(generated_content)
            
            # Сохраняем пост (новая простая система)
            save_success = await retry_helper.retry_async_operation(
                lambda: db.save_user_post(
                    telegram_id=telegram_id,
                    post_content=generated_content,
                    adapted_topic=content_data.get('adapted_topic', ''),
                    user_question=content_data.get('question', ''),
                    user_answer=user_answer
                )
            )
            
            if not save_success:
                logger.warning(f"Не удалось сохранить пост для пользователя {telegram_id}")
                return False, messages.ERROR_POST_GENERATION
            
            # Получаем обновленную информацию о лимитах после сохранения поста
            updated_limit_info = await retry_helper.retry_async_operation(
                lambda: db.check_user_post_limit(telegram_id)
            )
            
            remaining_attempts = updated_limit_info.get('posts_limit', 10) - updated_limit_info.get('posts_generated', 0)
            
            return True, messages.GENERATED_POST.format(
                generated_content=generated_content,
                remaining_attempts=remaining_attempts
            )
            
        except Exception as e:
            logger.error(f"Ошибка при генерации поста для пользователя {telegram_id}: {e}")
            return False, messages.ERROR_POST_GENERATION

# Создаем глобальный экземпляр системы постов
post_system = PostSystem()
