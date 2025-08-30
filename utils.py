# -*- coding: utf-8 -*-
"""
Утилиты для Telegram бота
"""

import re
import logging
import asyncio
import requests
import openai
from typing import Optional, Tuple
from telegram import File
from config import (
    EMAIL_REGEX, 
    OPENAI_API_KEY, 
    N8N_NICHE_WEBHOOK_URL,
    N8N_TOPIC_WEBHOOK_URL, 
    N8N_POST_WEBHOOK_URL,
    MAX_RETRIES, 
    RETRY_DELAY,
    OPENAI_TRANSCRIPTION_MODEL
)
from admin_notifier import notify_n8n_timeout, notify_n8n_error

logger = logging.getLogger(__name__)

# Настройка OpenAI
openai.api_key = OPENAI_API_KEY

class EmailValidator:
    """Класс для валидации email адресов"""
    
    @staticmethod
    def extract_email_from_text(text: str) -> Optional[str]:
        """
        Извлекает email из текста пользователя
        
        Args:
            text (str): Текст от пользователя
            
        Returns:
            Optional[str]: Найденный email или None
        """
        # Убираем лишние пробелы и переводим в нижний регистр
        text = text.strip().lower()
        
        # Ищем email в тексте с помощью regex
        email_matches = re.findall(EMAIL_REGEX, text)
        
        if email_matches:
            # Возвращаем первый найденный email
            return email_matches[0].lower()
        
        # Если прямого совпадения нет, попробуем найти email среди слов
        words = text.split()
        for word in words:
            # Убираем возможные знаки препинания в конце
            clean_word = re.sub(r'[^\w@.-]', '', word)
            if re.match(EMAIL_REGEX, clean_word):
                return clean_word.lower()
        
        return None
    
    @staticmethod
    def is_valid_email(email: str) -> bool:
        """
        Проверяет, является ли строка валидным email
        
        Args:
            email (str): Строка для проверки
            
        Returns:
            bool: True если email валиден
        """
        return bool(re.match(EMAIL_REGEX, email.lower()))

class VoiceProcessor:
    """Класс для обработки голосовых сообщений"""
    
    @staticmethod
    async def transcribe_voice_message(voice_file: File) -> Optional[str]:
        """
        Транскрибирует голосовое сообщение используя OpenAI Whisper
        
        Args:
            voice_file (File): Файл голосового сообщения
            
        Returns:
            Optional[str]: Транскрибированный текст или None при ошибке
        """
        try:
            # Скачиваем файл
            voice_bytes = await voice_file.download_as_bytearray()
            
            # Создаем временный файл в системной temp директории
            import tempfile
            import os
            
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                temp_filename = temp_file.name
                temp_file.write(voice_bytes)
            
            try:
                # Транскрибируем с помощью OpenAI Whisper
                with open(temp_filename, 'rb') as audio_file:
                    client = openai.OpenAI()
                    transcript = client.audio.transcriptions.create(
                        model=OPENAI_TRANSCRIPTION_MODEL,
                        file=audio_file,
                        language="ru"  # Указываем русский язык
                    )
            finally:
                # Всегда удаляем временный файл, даже при ошибке
                if os.path.exists(temp_filename):
                    os.remove(temp_filename)
            
            transcribed_text = transcript.text.strip()
            logger.info(f"Голосовое сообщение успешно транскрибировано: {transcribed_text[:100]}...")
            
            return transcribed_text
            
        except Exception as e:
            logger.error(f"Ошибка при транскрибации голосового сообщения: {e}")
            return None

class NicheDetector:
    """Класс для определения ниши через N8N webhook с callback"""
    
    @staticmethod
    async def detect_niche(description: str) -> Optional[str]:
        """
        Отправляет описание деятельности в N8N webhook для определения ниши
        Использует асинхронную архитектуру с callback
        
        Args:
            description (str): Описание деятельности пользователя
            
        Returns:
            Optional[str]: Определенная ниша или None при ошибке
        """
        try:
            from webhook_server import callback_manager
            
            payload = {
                'description': description,
                'language': 'ru'
            }
            
            logger.info(f"Отправляю асинхронный запрос для определения ниши")
            logger.debug(f"Payload: {payload}")
            
            # Отправляем асинхронный запрос в N8N
            request_id = await callback_manager.send_async_request(
                N8N_NICHE_WEBHOOK_URL,
                payload,
                "niche"
            )
            
            # Ждем callback от N8N
            logger.info(f"Ожидаю callback от N8N для request_id: {request_id}")
            result = await callback_manager.wait_for_callback(request_id, timeout=180)
            
            if result and result.get('success'):
                niche = result.get('niche', '').strip()
                if niche:
                    logger.info(f"Ниша успешно определена: {niche}")
                    return niche
                else:
                    logger.warning("N8N вернул пустую нишу через callback")
                    return None
            else:
                logger.error("Не получен callback от N8N или произошла ошибка")
                return None
                
        except Exception as e:
            logger.error(f"Неожиданная ошибка при определении ниши: {e}")
            return None

class RetryHelper:
    """Класс для повторных попыток выполнения операций"""
    
    @staticmethod
    async def retry_async_operation(operation, max_retries: int = MAX_RETRIES, delay: float = RETRY_DELAY):
        """
        Выполняет асинхронную операцию с повторными попытками
        
        Args:
            operation: Асинхронная функция для выполнения
            max_retries (int): Максимальное количество попыток
            delay (float): Задержка между попытками в секундах
            
        Returns:
            Результат выполнения операции
            
        Raises:
            Exception: Если все попытки неудачны
        """
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return await operation()
            except Exception as e:
                last_exception = e
                if attempt < max_retries:
                    logger.warning(f"Попытка {attempt + 1} неудачна: {e}. Повтор через {delay} сек...")
                    await asyncio.sleep(delay)
                    delay *= 2  # Экспоненциальная задержка
                else:
                    logger.error(f"Все {max_retries + 1} попыток неудачны")
        
        # Если дошли до этой точки, все попытки неудачны
        raise last_exception

class TextFormatter:
    """Класс для форматирования текста"""
    
    @staticmethod
    def escape_html(text: str) -> str:
        """
        Экранирует HTML символы в тексте
        
        Args:
            text (str): Исходный текст
            
        Returns:
            str: Текст с экранированными HTML символами
        """
        if not text:
            return ""
        
        text = str(text)
        text = text.replace('&', '&amp;')
        text = text.replace('<', '&lt;')
        text = text.replace('>', '&gt;')
        text = text.replace('"', '&quot;')
        text = text.replace("'", '&#x27;')
        
        return text
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 100) -> str:
        """
        Обрезает текст до указанной длины
        
        Args:
            text (str): Исходный текст
            max_length (int): Максимальная длина
            
        Returns:
            str: Обрезанный текст
        """
        if not text or len(text) <= max_length:
            return text
        
        return text[:max_length - 3] + "..."

# Создаем экземпляры утилит для удобного использования
email_validator = EmailValidator()
voice_processor = VoiceProcessor()
niche_detector = NicheDetector()
retry_helper = RetryHelper()
text_formatter = TextFormatter()
