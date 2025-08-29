# -*- coding: utf-8 -*-
"""
Главный файл для запуска Telegram бота с планировщиком напоминаний
"""

import asyncio
import logging
import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import json
from datetime import datetime

from bot import TelegramBot
from scheduler import scheduler
from config import LOG_LEVEL, LOG_FORMAT

# Настройка логирования
logging.basicConfig(
    format=LOG_FORMAT,
    level=getattr(logging, LOG_LEVEL)
)
logger = logging.getLogger(__name__)

class HealthCheckHandler(BaseHTTPRequestHandler):
    """Handler для health check endpoint"""
    
    def do_GET(self):
        if self.path == '/health':
            # Проверяем статус бота
            status = {
                "status": "healthy" if bot_manager.is_running else "unhealthy",
                "timestamp": datetime.now().isoformat(),
                "bot_running": bot_manager.is_running,
                "scheduler_running": scheduler.running if hasattr(scheduler, 'running') else True
            }
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status).encode())
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        # Отключаем стандартное логирование HTTP сервера
        pass

class BotManager:
    """Менеджер для управления ботом и планировщиком"""
    
    def __init__(self):
        self.bot = TelegramBot()
        self.scheduler_task = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.is_running = False
        self.health_server = None
        self.health_thread = None
    
    async def start_scheduler(self):
        """Запуск планировщика в отдельной задаче"""
        try:
            logger.info("Запуск планировщика напоминаний...")
            self.scheduler_task = scheduler.start()
            await self.scheduler_task
        except Exception as e:
            logger.error(f"Ошибка в планировщике: {e}")
    
    def start_bot(self):
        """Запуск бота в отдельном потоке"""
        try:
            logger.info("Запуск Telegram бота...")
            self.bot.run()
        except Exception as e:
            logger.error(f"Ошибка в боте: {e}")
    
    def start_health_server(self):
        """Запуск health check сервера"""
        try:
            self.health_server = HTTPServer(('0.0.0.0', 8080), HealthCheckHandler)
            logger.info("Health check сервер запущен на порту 8080")
            self.health_server.serve_forever()
        except Exception as e:
            logger.error(f"Ошибка в health check сервере: {e}")
    
    def stop_health_server(self):
        """Остановка health check сервера"""
        if self.health_server:
            self.health_server.shutdown()
            self.health_server.server_close()
            logger.info("Health check сервер остановлен")
    
    async def start(self):
        """Запуск бота, планировщика и health check сервера"""
        self.is_running = True
        
        # Запускаем health check сервер в отдельном потоке
        loop = asyncio.get_event_loop()
        health_future = loop.run_in_executor(self.executor, self.start_health_server)
        
        # Запускаем бота в отдельном потоке
        bot_future = loop.run_in_executor(self.executor, self.start_bot)
        
        # Запускаем планировщик в текущем цикле событий
        scheduler_future = self.start_scheduler()
        
        try:
            # Ждем завершения любой из задач
            done, pending = await asyncio.wait(
                [bot_future, scheduler_future, health_future],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Отменяем незавершенные задачи
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        except Exception as e:
            logger.error(f"Критическая ошибка: {e}")
        
        finally:
            await self.stop()
    
    async def stop(self):
        """Остановка бота, планировщика и health check сервера"""
        if not self.is_running:
            return
        
        logger.info("Остановка сервисов...")
        self.is_running = False
        
        # Останавливаем health check сервер
        self.stop_health_server()
        
        # Останавливаем планировщик
        scheduler.stop()
        
        if self.scheduler_task and not self.scheduler_task.done():
            self.scheduler_task.cancel()
            try:
                await self.scheduler_task
            except asyncio.CancelledError:
                pass
        
        # Останавливаем executor
        self.executor.shutdown(wait=True)
        
        logger.info("Все сервисы остановлены")

# Глобальный экземпляр менеджера
bot_manager = BotManager()

def signal_handler(signum, frame):
    """Обработчик сигналов для graceful shutdown"""
    logger.info(f"Получен сигнал {signum}, завершение работы...")
    
    # Создаем новый event loop если его нет
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    # Запускаем остановку
    if loop.is_running():
        loop.create_task(bot_manager.stop())
    else:
        loop.run_until_complete(bot_manager.stop())
    
    sys.exit(0)

async def main():
    """Главная функция"""
    
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Инициализация бота и планировщика...")
    
    try:
        await bot_manager.start()
    except KeyboardInterrupt:
        logger.info("Получен сигнал прерывания")
    except Exception as e:
        logger.error(f"Критическая ошибка в main: {e}")
    finally:
        await bot_manager.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Программа прервана пользователем")
    except Exception as e:
        logger.error(f"Фатальная ошибка: {e}")
        sys.exit(1)
