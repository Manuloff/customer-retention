from typing import Callable, Dict, Any, Awaitable, Optional

from aiogram import types
from aiogram.dispatcher.middlewares.base import BaseMiddleware

from src.models import User
from src.repositories import Repositories


class UserMiddleware(BaseMiddleware):
    async def __call__(
            self,
            handler: Callable[[types.TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: types.TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        repos: Repositories = data.get('repos')

        if not repos:
            return await handler(event, data)

        user_id = None
        if isinstance(event, types.Message) or isinstance(event, types.CallbackQuery):
            user_id = event.from_user.id

        user: Optional['User'] = None
        if user_id:
            async with repos.database:
                try:
                    user = await repos.users.get_one(user_id)

                except Exception as e:
                    print(f"Ошибка загрузки пользователя {user_id}: {e}")

                if not user:
                    user = User(user_id, "client")

                    try:
                        await repos.users.insert(user)

                    except Exception as e:
                        print(f"Ошибка добавления пользователя {user_id}: {e}")


        data["user"] = user

        return await handler(event, data)