from aiogram import types
from aiogram.filters import Filter

from src.models import User


class RoleFilter(Filter):
    def __init__(self, required_role: str) -> None:
        self.required_role = required_role

    async def __call__(self, event: types.TelegramObject, **kwargs) -> bool:
        user: 'User' = kwargs.get('user')

        if user is None:
            return self.required_role == 'client'

        return user.role == self.required_role