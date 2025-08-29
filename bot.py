# -*- coding: utf-8 -*-
"""
Основной файл Telegram бота для определения ниши пользователей
"""

import logging
import asyncio
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    filters,
    ContextTypes
)

# Импорты локальных модулей
from config import (
    TELEGRAM_BOT_TOKEN, 
    BotStates, 
    NICHE_CONFIRMATION_KEYBOARD,
    MAIN_MENU_KEYBOARD,
    PROFILE_KEYBOARD,
    MAX_USERS,
    LOG_LEVEL,
    LOG_FORMAT
)
from database import db
from utils import email_validator, voice_processor, niche_detector, retry_helper, text_formatter
from error_handler import (
    telegram_error_handler, 
    rate_limit_handler, 
    global_rate_limiter,
    BotErrorHandler
)
from post_system import post_system, N8NTimeoutError, N8NConnectionError
import messages

# Настройка логирования
logging.basicConfig(
    format=LOG_FORMAT,
    level=getattr(logging, LOG_LEVEL)
)
logger = logging.getLogger(__name__)

class TelegramBot:
    """Основной класс Telegram бота"""
    
    def __init__(self):
        """Инициализация бота"""
        self.app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        
        # Команды
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("profile", self.profile_command))
        
        # Обработчики кнопок
        self.app.add_handler(CallbackQueryHandler(self.handle_callback_query))
        
        # Обработчики сообщений по состояниям
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_text_message
        ))
        
        # Обработчик голосовых сообщений
        self.app.add_handler(MessageHandler(
            filters.VOICE, 
            self.handle_voice_message
        ))
        
        # Обработчик кнопок главного меню
        self.app.add_handler(MessageHandler(
            filters.Regex("^👤 Профиль$"),
            self.profile_command
        ))
        
        # Обработчик ошибок
        self.app.add_error_handler(self.error_handler)
    
    @telegram_error_handler
    @rate_limit_handler(global_rate_limiter)
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        try:
            user = update.effective_user
            telegram_id = user.id
            
            # Проверяем лимит пользователей
            users_count = await retry_helper.retry_async_operation(
                lambda: db.get_users_count()
            )
            
            if users_count >= MAX_USERS:
                await update.message.reply_text(
                    "<b>❌ Достигнут лимит пользователей</b>\n\n"
                    "К сожалению, мы достигли максимального количества пользователей. "
                    "Пожалуйста, попробуйте позже.",
                    parse_mode='HTML'
                )
                return
            
            # Проверяем, существует ли пользователь
            existing_user = await retry_helper.retry_async_operation(
                lambda: db.get_user_by_telegram_id(telegram_id)
            )
            
            if existing_user:
                # Пользователь уже зарегистрирован
                if existing_user['state'] == BotStates.REGISTERED:
                    await self.show_main_menu(update, context)
                else:
                    # Продолжаем регистрацию с текущего состояния
                    await self.continue_registration(update, context, existing_user)
            else:
                # Новый пользователь - начинаем регистрацию
                await update.message.reply_text(
                    messages.WELCOME_MESSAGE,
                    parse_mode='HTML'
                )
                
        except Exception as e:
            logger.error(f"Ошибка в start_command: {e}")
            raise  # Позволяем декоратору обработать ошибку
    
    @telegram_error_handler
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = """
<b>🤖 Помощь по боту</b>

<b>Команды:</b>
• /start - Начать работу или вернуться в главное меню
• /profile - Показать профиль
• /help - Показать эту справку

<b>Возможности:</b>
• 📧 Регистрация по email адресу
• 🎯 Определение вашей ниши деятельности
• 💬 Поддержка голосовых сообщений
• ⏰ Ежедневные напоминания о постах

<b>Поддержка:</b>
Если у вас возникли проблемы, обратитесь в поддержку.
        """
        
        await update.message.reply_text(help_text, parse_mode='HTML')
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        try:
            user = update.effective_user
            telegram_id = user.id
            text = update.message.text.strip()
            
            # Получаем текущего пользователя
            current_user = await retry_helper.retry_async_operation(
                lambda: db.get_user_by_telegram_id(telegram_id)
            )
            
            if not current_user:
                # Пользователь не найден - начинаем с email
                await self.handle_email_input(update, context, text)
            else:
                # Обрабатываем в зависимости от состояния
                state = current_user.get('state', BotStates.WAITING_EMAIL)
                
                if state == BotStates.WAITING_EMAIL:
                    await self.handle_email_input(update, context, text)
                elif state == BotStates.WAITING_NICHE_DESCRIPTION:
                    await self.handle_niche_description(update, context, text)
                elif state == BotStates.WAITING_POST_ANSWER:
                    await self.handle_post_answer(update, context, text)
                elif state == BotStates.REGISTERED:
                    await self.handle_registered_user_message(update, context, text)
                else:
                    # Неизвестное состояние - отправляем в начало
                    await update.message.reply_text(
                        "Используйте /start для начала работы",
                        parse_mode='HTML'
                    )
        
        except Exception as e:
            logger.error(f"Ошибка в handle_text_message: {e}")
            await update.message.reply_text(
                messages.ERROR_GENERAL,
                parse_mode='HTML'
            )
    
    async def handle_email_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка ввода email"""
        try:
            user = update.effective_user
            telegram_id = user.id
            
            # Извлекаем email из текста
            email = email_validator.extract_email_from_text(text)
            
            if not email:
                # Email не найден в тексте
                await update.message.reply_text(
                    messages.INVALID_EMAIL.format(
                        input_text=text_formatter.escape_html(text[:50])
                    ),
                    parse_mode='HTML'
                )
                return
            
            # Проверяем валидность email
            if not email_validator.is_valid_email(email):
                await update.message.reply_text(
                    messages.INVALID_EMAIL.format(
                        input_text=text_formatter.escape_html(text[:50])
                    ),
                    parse_mode='HTML'
                )
                return
            
            # Проверяем email в базе данных
            email_exists = await retry_helper.retry_async_operation(
                lambda: db.check_email_exists(email)
            )
            
            if not email_exists:
                await update.message.reply_text(
                    messages.EMAIL_NOT_FOUND.format(
                        email=text_formatter.escape_html(email)
                    ),
                    parse_mode='HTML'
                )
                return
            
            # Email найден - создаем или обновляем пользователя
            existing_user = await retry_helper.retry_async_operation(
                lambda: db.get_user_by_telegram_id(telegram_id)
            )
            
            if not existing_user:
                # Создаем нового пользователя
                await retry_helper.retry_async_operation(
                    lambda: db.create_user(
                        telegram_id=telegram_id,
                        email=email,
                        username=user.username,
                        first_name=user.first_name,
                        last_name=user.last_name
                    )
                )
            else:
                # Обновляем состояние существующего пользователя
                await retry_helper.retry_async_operation(
                    lambda: db.update_user_state(telegram_id, BotStates.WAITING_NICHE_DESCRIPTION)
                )
            
            # Отправляем сообщение об успехе и просим описать нишу
            await update.message.reply_text(
                messages.EMAIL_SUCCESS.format(
                    email=text_formatter.escape_html(email)
                ),
                parse_mode='HTML'
            )
            
            await asyncio.sleep(1)  # Небольшая пауза для лучшего UX
            
            await update.message.reply_text(
                messages.NICHE_REQUEST,
                parse_mode='HTML'
            )
        
        except Exception as e:
            logger.error(f"Ошибка в handle_email_input: {e}")
            await update.message.reply_text(
                messages.ERROR_DATABASE,
                parse_mode='HTML'
            )
    
    async def handle_niche_description(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка описания ниши"""
        try:
            user = update.effective_user
            telegram_id = user.id
            
            # Показываем сообщение о процессе анализа
            processing_message = await update.message.reply_text(
                messages.NICHE_PROCESSING,
                parse_mode='HTML'
            )
            
            # Определяем нишу через N8N webhook
            niche = await niche_detector.detect_niche(text)
            
            if not niche:
                # Ошибка определения ниши
                await processing_message.edit_text(
                    messages.ERROR_N8N_WEBHOOK,
                    parse_mode='HTML'
                )
                return
            
            # Сохраняем предварительную нишу в контексте
            context.user_data['temp_niche'] = niche
            
            # Создаем кнопки для подтверждения
            keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton(messages.BUTTON_CORRECT, callback_data='niche_correct'),
                    InlineKeyboardButton(messages.BUTTON_TRY_AGAIN, callback_data='niche_retry')
                ]
            ])
            
            # Показываем результат с кнопками
            await processing_message.edit_text(
                messages.NICHE_RESULT.format(
                    niche=text_formatter.escape_html(niche)
                ),
                parse_mode='HTML',
                reply_markup=keyboard
            )
        
        except Exception as e:
            logger.error(f"Ошибка в handle_niche_description: {e}")
            await update.message.reply_text(
                messages.ERROR_N8N_WEBHOOK,
                parse_mode='HTML'
            )
    
    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик голосовых сообщений"""
        try:
            user = update.effective_user
            telegram_id = user.id
            
            # Проверяем состояние пользователя
            current_user = await retry_helper.retry_async_operation(
                lambda: db.get_user_by_telegram_id(telegram_id)
            )
            
            state = current_user.get('state') if current_user else None
            
            if state not in [BotStates.WAITING_NICHE_DESCRIPTION, BotStates.WAITING_POST_ANSWER]:
                await update.message.reply_text(
                    "Голосовые сообщения принимаются при описании ниши или ответе на вопрос для поста.",
                    parse_mode='HTML'
                )
                return
            
            # Показываем сообщение о процессе обработки
            processing_message = await update.message.reply_text(
                "🎤 Обрабатываю голосовое сообщение...",
                parse_mode='HTML'
            )
            
            # Получаем файл голосового сообщения
            voice_file = await update.message.voice.get_file()
            
            # Транскрибируем голосовое сообщение
            transcribed_text = await voice_processor.transcribe_voice_message(voice_file)
            
            if not transcribed_text:
                await processing_message.edit_text(
                    messages.ERROR_VOICE_TRANSCRIPTION,
                    parse_mode='HTML'
                )
                return
            
            # Удаляем сообщение о процессе
            await processing_message.delete()
            
            # Обрабатываем транскрибированный текст в зависимости от состояния
            if state == BotStates.WAITING_NICHE_DESCRIPTION:
                await self.handle_niche_description(update, context, transcribed_text)
            elif state == BotStates.WAITING_POST_ANSWER:
                await self.handle_post_answer(update, context, transcribed_text)
        
        except Exception as e:
            logger.error(f"Ошибка в handle_voice_message: {e}")
            await update.message.reply_text(
                messages.ERROR_VOICE_TRANSCRIPTION,
                parse_mode='HTML'
            )
    
    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик callback query от inline кнопок"""
        try:
            query = update.callback_query
            await query.answer()
            
            user = query.from_user
            telegram_id = user.id
            data = query.data
            
            if data == 'niche_correct':
                # Пользователь подтвердил нишу
                temp_niche = context.user_data.get('temp_niche')
                
                if temp_niche:
                    # Сохраняем нишу в базу данных
                    await retry_helper.retry_async_operation(
                        lambda: db.update_user_niche(telegram_id, temp_niche)
                    )
                    
                    # Обновляем состояние пользователя
                    await retry_helper.retry_async_operation(
                        lambda: db.update_user_state(telegram_id, BotStates.REGISTERED)
                    )
                    
                    # Очищаем временные данные
                    context.user_data.clear()
                    
                    # Отправляем сообщение о сохранении
                    await query.edit_message_text(
                        messages.NICHE_SAVED.format(
                            niche=text_formatter.escape_html(temp_niche)
                        ),
                        parse_mode='HTML'
                    )
                    
                    await asyncio.sleep(1)
                    
                    # Показываем информацию о напоминаниях
                    await query.message.reply_text(
                        messages.REMINDER_SETUP,
                        parse_mode='HTML'
                    )
                    
                    await asyncio.sleep(1)
                    
                    # Показываем главное меню
                    await self.show_main_menu_after_registration(query, context)
                
            elif data == 'niche_retry':
                # Пользователь хочет попробовать еще раз
                await query.edit_message_text(
                    messages.NICHE_RETRY,
                    parse_mode='HTML'
                )
                
                # Очищаем временные данные
                context.user_data.pop('temp_niche', None)
            
            elif data == 'change_niche':
                # Пользователь хочет изменить нишу
                await retry_helper.retry_async_operation(
                    lambda: db.update_user_state(telegram_id, BotStates.WAITING_NICHE_DESCRIPTION)
                )
                
                await query.edit_message_text(
                    messages.NICHE_REQUEST,
                    parse_mode='HTML'
                )
            
            elif data == 'suggest_topic':
                # Пользователь запросил предложение темы
                await self.handle_suggest_topic(query, context)
            
            elif data == 'write_post':
                # Пользователь хочет написать пост
                await self.handle_write_post_request(query, context)
            
            elif data == 'regenerate_post':
                # Пользователь хочет пересоздать пост
                await self.handle_regenerate_post(query, context)
            
            elif data == 'new_topic':
                # Пользователь хочет новую тему
                await self.handle_suggest_topic(query, context)
        
        except Exception as e:
            logger.error(f"Ошибка в handle_callback_query: {e}")
            await query.message.reply_text(
                messages.ERROR_GENERAL,
                parse_mode='HTML'
            )
    
    async def profile_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать профиль пользователя"""
        try:
            user = update.effective_user
            telegram_id = user.id
            
            # Получаем данные пользователя
            current_user = await retry_helper.retry_async_operation(
                lambda: db.get_user_by_telegram_id(telegram_id)
            )
            
            if not current_user:
                await update.message.reply_text(
                    "Пользователь не найден. Используйте /start для регистрации.",
                    parse_mode='HTML'
                )
                return
            
            # Получаем информацию о лимитах постов
            limit_info = await retry_helper.retry_async_operation(
                lambda: db.check_user_post_limit(telegram_id)
            )
            
            # Форматируем дату регистрации
            reg_date = current_user.get('registration_date', 'Неизвестно')
            if reg_date and reg_date != 'Неизвестно':
                try:
                    parsed_date = datetime.fromisoformat(reg_date.replace('Z', '+00:00'))
                    reg_date = parsed_date.strftime('%d.%m.%Y')
                except:
                    reg_date = 'Неизвестно'
            
            # Создаем кнопки профиля
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(messages.BUTTON_CHANGE_NICHE, callback_data='change_niche')]
            ])
            
            # Отправляем информацию о профиле
            profile_text = messages.PROFILE_INFO.format(
                email=text_formatter.escape_html(current_user.get('email', 'Не указан')),
                niche=text_formatter.escape_html(current_user.get('niche', 'Не определена')),
                subscription=messages.SUBSCRIPTION_INACTIVE,  # Пока что неактивна
                registration_date=reg_date,
                posts_generated=limit_info.get('posts_generated', 0),
                posts_limit=limit_info.get('posts_limit', 10),
                remaining_posts=limit_info.get('remaining_posts', 10)
            )
            
            await update.message.reply_text(
                profile_text,
                parse_mode='HTML',
                reply_markup=keyboard
            )
        
        except Exception as e:
            logger.error(f"Ошибка в profile_command: {e}")
            await update.message.reply_text(
                messages.ERROR_DATABASE,
                parse_mode='HTML'
            )
    
    async def show_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать главное меню для зарегистрированного пользователя"""
        keyboard = ReplyKeyboardMarkup(
            MAIN_MENU_KEYBOARD,
            resize_keyboard=True,
            one_time_keyboard=False
        )
        
        await update.message.reply_text(
            "<b>🏠 Главное меню</b>\n\nВыберите действие:",
            parse_mode='HTML',
            reply_markup=keyboard
        )
    
    async def show_main_menu_after_registration(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Показать главное меню после регистрации"""
        keyboard = ReplyKeyboardMarkup(
            MAIN_MENU_KEYBOARD,
            resize_keyboard=True,
            one_time_keyboard=False
        )
        
        await query.message.reply_text(
            "<b>🏠 Главное меню</b>\n\nТеперь вы можете использовать бота!",
            parse_mode='HTML',
            reply_markup=keyboard
        )
    
    async def continue_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict):
        """Продолжить регистрацию с текущего состояния"""
        state = user_data.get('state', BotStates.WAITING_EMAIL)
        
        if state == BotStates.WAITING_EMAIL:
            await update.message.reply_text(
                messages.WELCOME_MESSAGE,
                parse_mode='HTML'
            )
        elif state == BotStates.WAITING_NICHE_DESCRIPTION:
            await update.message.reply_text(
                messages.NICHE_REQUEST,
                parse_mode='HTML'
            )
        else:
            await self.show_main_menu(update, context)
    
    async def handle_registered_user_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка сообщений от зарегистрированных пользователей"""
        # Пока что просто показываем главное меню
        await self.show_main_menu(update, context)
    
    async def handle_suggest_topic(self, query_or_update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка запроса на предложение темы"""
        try:
            # Определяем тип объекта (CallbackQuery или Update)
            if hasattr(query_or_update, 'from_user'):
                # Это CallbackQuery
                user = query_or_update.from_user
                message = query_or_update.message
                is_callback = True
            else:
                # Это Update
                user = query_or_update.effective_user
                message = query_or_update.effective_message
                is_callback = False
            
            telegram_id = user.id
            
            # Получаем данные пользователя
            current_user = await retry_helper.retry_async_operation(
                lambda: db.get_user_by_telegram_id(telegram_id)
            )
            
            if not current_user:
                error_text = "Пользователь не найден. Используйте /start для регистрации."
                if is_callback:
                    await query_or_update.edit_message_text(error_text, parse_mode='HTML')
                else:
                    await message.reply_text(error_text, parse_mode='HTML')
                return
            
            niche = current_user.get('niche')
            if not niche:
                error_text = "Сначала необходимо определить вашу нишу. Используйте /start."
                if is_callback:
                    await query_or_update.edit_message_text(error_text, parse_mode='HTML')
                else:
                    await message.reply_text(error_text, parse_mode='HTML')
                return
            
            # Показываем сообщение о процессе
            if is_callback:
                await query_or_update.edit_message_text(
                    messages.SUGGEST_TOPIC_PROCESSING,
                    parse_mode='HTML'
                )
            else:
                processing_message = await message.reply_text(
                    messages.SUGGEST_TOPIC_PROCESSING,
                    parse_mode='HTML'
                )
            
            # Обрабатываем запрос темы
            success, response_text, content_data = await post_system.process_topic_request(telegram_id, niche)
            
            if success and content_data:
                # Сохраняем данные контента в контексте
                context.user_data['current_content'] = content_data
                
                # Создаем кнопку "Написать пост"
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(messages.BUTTON_WRITE_POST, callback_data='write_post')],
                    [InlineKeyboardButton(messages.BUTTON_NEW_TOPIC, callback_data='new_topic')]
                ])
                
                if is_callback:
                    await query_or_update.edit_message_text(
                        response_text,
                        parse_mode='HTML',
                        reply_markup=keyboard
                    )
                else:
                    await processing_message.edit_text(
                        response_text,
                        parse_mode='HTML',
                        reply_markup=keyboard
                    )
            else:
                # Ошибка, лимит превышен или таймаут
                # При таймауте добавляем кнопку повтора
                keyboard = None
                if "время ожидания" in response_text or "не отвечает" in response_text:
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Попробовать еще раз", callback_data='suggest_topic')]
                    ])
                
                if is_callback:
                    await query_or_update.edit_message_text(
                        response_text,
                        parse_mode='HTML',
                        reply_markup=keyboard
                    )
                else:
                    await processing_message.edit_text(
                        response_text,
                        parse_mode='HTML',
                        reply_markup=keyboard
                    )
        
        except Exception as e:
            logger.error(f"Ошибка в handle_suggest_topic: {e}")
            error_text = messages.ERROR_GENERAL
            if hasattr(query_or_update, 'edit_message_text'):
                await query_or_update.edit_message_text(error_text, parse_mode='HTML')
            else:
                await query_or_update.effective_message.reply_text(error_text, parse_mode='HTML')
    
    async def handle_write_post_request(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработка запроса на написание поста"""
        try:
            user = query.from_user
            telegram_id = user.id
            
            # Получаем данные контента из контекста
            content_data = context.user_data.get('current_content')
            if not content_data:
                await query.edit_message_text(
                    "Данные контента не найдены. Пожалуйста, запросите тему заново.",
                    parse_mode='HTML'
                )
                return
            
            # Переводим пользователя в состояние ожидания ответа
            await retry_helper.retry_async_operation(
                lambda: db.update_user_state(telegram_id, BotStates.WAITING_POST_ANSWER)
            )
            
            # Отправляем вопрос пользователю
            question_text = messages.POST_QUESTION.format(
                topic=text_formatter.escape_html(content_data.get('adapted_topic', content_data.get('topic'))),
                question=text_formatter.escape_html(content_data.get('question', ''))
            )
            
            await query.edit_message_text(
                question_text,
                parse_mode='HTML'
            )
        
        except Exception as e:
            logger.error(f"Ошибка в handle_write_post_request: {e}")
            await query.edit_message_text(
                messages.ERROR_GENERAL,
                parse_mode='HTML'
            )
    
    async def handle_post_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
        """Обработка ответа пользователя на вопрос для поста"""
        try:
            user = update.effective_user
            telegram_id = user.id
            
            # Получаем данные контента из контекста
            content_data = context.user_data.get('current_content')
            if not content_data:
                await update.message.reply_text(
                    "Данные контента не найдены. Пожалуйста, запросите тему заново через /start.",
                    parse_mode='HTML'
                )
                return
            
            # Получаем данные пользователя
            current_user = await retry_helper.retry_async_operation(
                lambda: db.get_user_by_telegram_id(telegram_id)
            )
            
            if not current_user:
                await update.message.reply_text(
                    "Пользователь не найден. Используйте /start для регистрации.",
                    parse_mode='HTML'
                )
                return
            
            niche = current_user.get('niche')
            
            # Показываем сообщение о процессе генерации
            processing_message = await update.message.reply_text(
                messages.POST_PROCESSING,
                parse_mode='HTML'
            )
            
            # Генерируем пост
            success, response_text = await post_system.process_post_generation(
                telegram_id=telegram_id,
                niche=niche,
                content_data=content_data,
                user_answer=text
            )
            
            if success:
                # Переводим пользователя в состояние "пост сгенерирован"
                await retry_helper.retry_async_operation(
                    lambda: db.update_user_state(telegram_id, BotStates.POST_GENERATED)
                )
                
                # Создаем кнопку "Заново"
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(messages.BUTTON_REGENERATE, callback_data='regenerate_post')],
                    [InlineKeyboardButton(messages.BUTTON_NEW_TOPIC, callback_data='new_topic')]
                ])
                
                await processing_message.edit_text(
                    response_text,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
            else:
                # Ошибка генерации или таймаут
                # Возвращаем состояние для повторного ответа
                await retry_helper.retry_async_operation(
                    lambda: db.update_user_state(telegram_id, BotStates.WAITING_POST_ANSWER)
                )
                
                # При таймауте добавляем кнопку повтора, при других ошибках - просто текст
                keyboard = None
                if "время ожидания" in response_text or "не отвечает" in response_text:
                    keyboard = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔄 Попробовать еще раз", callback_data='regenerate_post')]
                    ])
                
                await processing_message.edit_text(
                    response_text,
                    parse_mode='HTML',
                    reply_markup=keyboard
                )
        
        except Exception as e:
            logger.error(f"Ошибка в handle_post_answer: {e}")
            await update.message.reply_text(
                messages.ERROR_POST_GENERATION,
                parse_mode='HTML'
            )
    
    async def handle_regenerate_post(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработка запроса на повторную генерацию поста"""
        try:
            user = query.from_user
            telegram_id = user.id
            
            # Получаем данные контента из контекста
            content_data = context.user_data.get('current_content')
            if not content_data:
                await query.edit_message_text(
                    "Данные контента не найдены. Пожалуйста, запросите тему заново.",
                    parse_mode='HTML'
                )
                return
            
            # Переводим пользователя в состояние ожидания ответа
            await retry_helper.retry_async_operation(
                lambda: db.update_user_state(telegram_id, BotStates.WAITING_POST_ANSWER)
            )
            
            # Отправляем вопрос пользователю заново
            question_text = messages.POST_REGENERATE_QUESTION.format(
                topic=text_formatter.escape_html(content_data.get('adapted_topic', content_data.get('topic'))),
                question=text_formatter.escape_html(content_data.get('question', ''))
            )
            
            await query.edit_message_text(
                question_text,
                parse_mode='HTML'
            )
        
        except Exception as e:
            logger.error(f"Ошибка в handle_regenerate_post: {e}")
            await query.edit_message_text(
                messages.ERROR_GENERAL,
                parse_mode='HTML'
            )
    
    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        if isinstance(update, Update):
            await BotErrorHandler.handle_general_error(update, context, context.error)
        else:
            logger.error(f"Необработанная ошибка: {context.error}")
    
    async def run(self):
        """Запуск бота"""
        logger.info("Запуск Telegram бота...")
        try:
            await self.app.initialize()
            await self.app.start()
            await self.app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
            # Ждем до получения сигнала остановки
            # В новых версиях python-telegram-bot используется app.idle()
            await self.app.idle()
        except Exception as e:
            logger.error(f"Ошибка в async run: {e}")
        finally:
            try:
                if hasattr(self.app, 'updater') and self.app.updater.running:
                    await self.app.updater.stop()
                if hasattr(self.app, '_initialized') and self.app._initialized:
                    await self.app.stop()
                    await self.app.shutdown()
            except Exception as e:
                logger.error(f"Ошибка при остановке: {e}")
    
    def run_sync(self):
        """Синхронный запуск бота для использования в executor"""
        logger.info("Запуск Telegram бота...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)
    
    async def stop(self):
        """Остановка бота"""
        try:
            if hasattr(self.app, 'updater') and self.app.updater.running:
                await self.app.updater.stop()
            if hasattr(self.app, '_initialized') and self.app._initialized:
                await self.app.stop()
                await self.app.shutdown()
            logger.info("Бот остановлен")
        except Exception as e:
            logger.error(f"Ошибка при остановке бота: {e}")

# Создаем и запускаем бота
if __name__ == "__main__":
    import asyncio
    bot = TelegramBot()
    asyncio.run(bot.run())
