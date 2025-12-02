from typing import Callable, Dict, Any, Awaitable

from aiogram import types
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from src.repositories import Repositories


class RepoMiddleware(BaseMiddleware):
    def __init__(self, repos: Repositories):
        self.repos = repos

    async def __call__(
        self,
        handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: types.TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        data["repos"] = self.repos
        return await handler(event, data)