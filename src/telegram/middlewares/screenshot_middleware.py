from typing import Callable, Dict, Any, Awaitable

from aiogram import types
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from src.services import DashboardScreenshotService


class DashboardScreenshotMiddleware(BaseMiddleware):
    def __init__(self, screenshot_service: DashboardScreenshotService):
        self._screenshot_service = screenshot_service

    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        data["screenshot_service"] = self._screenshot_service
        return await handler(event, data)