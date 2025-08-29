# -*- coding: utf-8 -*-
"""
HTTP сервер для приема callback'ов от N8N
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from aiohttp import web, ClientSession
from aiohttp.web import Request, Response
import threading
import time

logger = logging.getLogger(__name__)

class CallbackManager:
    """Менеджер для управления callback'ами от N8N"""
    
    def __init__(self):
        self.pending_requests: Dict[str, Dict] = {}
        self.callback_handlers: Dict[str, Any] = {}
        self.app = None
        self.runner = None
        self.site = None
        
    def generate_request_id(self) -> str:
        """Генерация уникального ID для запроса"""
        return str(uuid.uuid4())
    
    async def send_async_request(self, webhook_url: str, payload: dict, callback_type: str) -> str:
        """
        Отправляет асинхронный запрос в N8N и возвращает request_id
        """
        request_id = self.generate_request_id()
        
        # Добавляем callback URL и request_id в payload
        callback_url = f"http://innokentiy-bot:8080/webhook/callback/{callback_type}"
        payload_with_callback = {
            **payload,
            "callback_url": callback_url,
            "request_id": request_id
        }
        
        # Сохраняем информацию о запросе
        self.pending_requests[request_id] = {
            "timestamp": datetime.now(),
            "callback_type": callback_type,
            "status": "pending"
        }
        
        try:
            async with ClientSession() as session:
                logger.info(f"Отправляю асинхронный запрос в N8N: {webhook_url}")
                logger.debug(f"Payload с callback: {payload_with_callback}")
                
                async with session.post(
                    webhook_url,
                    json=payload_with_callback,
                    timeout=30,  # Короткий таймаут, т.к. N8N должен быстро принять запрос
                    headers={'Content-Type': 'application/json'}
                ) as response:
                    if response.status == 200:
                        logger.info(f"N8N принял запрос {request_id} для обработки")
                    else:
                        logger.error(f"N8N отклонил запрос {request_id}: {response.status}")
                        self.pending_requests[request_id]["status"] = "failed"
                        
        except Exception as e:
            logger.error(f"Ошибка отправки запроса в N8N: {e}")
            self.pending_requests[request_id]["status"] = "failed"
            
        return request_id
    
    async def wait_for_callback(self, request_id: str, timeout: int = 180) -> Optional[Dict]:
        """
        Ждет callback от N8N в течение указанного времени
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if request_id in self.callback_handlers:
                result = self.callback_handlers.pop(request_id)
                self.pending_requests.pop(request_id, None)
                logger.info(f"Получен callback для запроса {request_id}")
                return result
                
            await asyncio.sleep(0.5)  # Проверяем каждые 0.5 секунд
        
        # Таймаут
        logger.warning(f"Таймаут ожидания callback для запроса {request_id}")
        self.pending_requests.pop(request_id, None)
        return None
    
    async def handle_niche_callback(self, request: Request) -> Response:
        """Обработчик callback для определения ниши"""
        try:
            data = await request.json()
            request_id = data.get('request_id')
            niche = data.get('niche', '').strip()
            
            logger.info(f"Получен callback для ниши: request_id={request_id}, niche={niche}")
            
            if request_id and request_id in self.pending_requests:
                self.callback_handlers[request_id] = {
                    "success": True,
                    "niche": niche,
                    "timestamp": datetime.now()
                }
                return web.json_response({"status": "ok"})
            else:
                logger.warning(f"Получен callback для неизвестного request_id: {request_id}")
                return web.json_response({"status": "error", "message": "Unknown request_id"}, status=400)
                
        except Exception as e:
            logger.error(f"Ошибка обработки niche callback: {e}")
            return web.json_response({"status": "error", "message": str(e)}, status=500)
    
    async def handle_topic_callback(self, request: Request) -> Response:
        """Обработчик callback для адаптации темы"""
        try:
            data = await request.json()
            request_id = data.get('request_id')
            adapted_topic = data.get('adapted_topic', '').strip()
            
            logger.info(f"Получен callback для темы: request_id={request_id}, topic={adapted_topic}")
            
            if request_id and request_id in self.pending_requests:
                self.callback_handlers[request_id] = {
                    "success": True,
                    "adapted_topic": adapted_topic,
                    "timestamp": datetime.now()
                }
                return web.json_response({"status": "ok"})
            else:
                logger.warning(f"Получен callback для неизвестного request_id: {request_id}")
                return web.json_response({"status": "error", "message": "Unknown request_id"}, status=400)
                
        except Exception as e:
            logger.error(f"Ошибка обработки topic callback: {e}")
            return web.json_response({"status": "error", "message": str(e)}, status=500)
    
    async def handle_post_callback(self, request: Request) -> Response:
        """Обработчик callback для генерации поста"""
        try:
            data = await request.json()
            request_id = data.get('request_id')
            generated_post = data.get('generated_post', '').strip()
            
            logger.info(f"Получен callback для поста: request_id={request_id}, post_length={len(generated_post)}")
            
            if request_id and request_id in self.pending_requests:
                self.callback_handlers[request_id] = {
                    "success": True,
                    "generated_post": generated_post,
                    "timestamp": datetime.now()
                }
                return web.json_response({"status": "ok"})
            else:
                logger.warning(f"Получен callback для неизвестного request_id: {request_id}")
                return web.json_response({"status": "error", "message": "Unknown request_id"}, status=400)
                
        except Exception as e:
            logger.error(f"Ошибка обработки post callback: {e}")
            return web.json_response({"status": "error", "message": str(e)}, status=500)
    
    async def health_check(self, request: Request) -> Response:
        """Health check endpoint"""
        return web.json_response({
            "status": "ok",
            "pending_requests": len(self.pending_requests),
            "service": "webhook_server"
        })
    
    async def init_app(self):
        """Инициализация aiohttp приложения"""
        self.app = web.Application()
        
        # Добавляем роуты
        self.app.router.add_post('/webhook/callback/niche', self.handle_niche_callback)
        self.app.router.add_post('/webhook/callback/topic', self.handle_topic_callback)  
        self.app.router.add_post('/webhook/callback/post', self.handle_post_callback)
        self.app.router.add_get('/health', self.health_check)
        
        return self.app
    
    async def start_server(self, host='0.0.0.0', port=8080):
        """Запуск webhook сервера"""
        try:
            await self.init_app()
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, host, port)
            await self.site.start()
            
            logger.info(f"Webhook сервер запущен на {host}:{port}")
            
        except Exception as e:
            logger.error(f"Ошибка запуска webhook сервера: {e}")
            raise
    
    async def stop_server(self):
        """Остановка webhook сервера"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("Webhook сервер остановлен")
    
    def cleanup_old_requests(self):
        """Очистка старых запросов (старше 5 минут)"""
        cutoff_time = datetime.now() - timedelta(minutes=5)
        old_requests = [
            req_id for req_id, req_info in self.pending_requests.items()
            if req_info['timestamp'] < cutoff_time
        ]
        
        for req_id in old_requests:
            self.pending_requests.pop(req_id, None)
            self.callback_handlers.pop(req_id, None)
            
        if old_requests:
            logger.info(f"Очищены старые запросы: {len(old_requests)}")

# Глобальный экземпляр
callback_manager = CallbackManager()
