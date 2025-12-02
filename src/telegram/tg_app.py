from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from src.config import Settings
from src.repositories import Repositories
from src.services import DashboardScreenshotService
from src.telegram.filters import RoleFilter
from src.telegram.middlewares import RepoMiddleware, UserMiddleware, DashboardScreenshotMiddleware
from src.telegram.router import create_admin_router, create_client_router


class TelegramApp:
    def __init__(self, repositories: Repositories, screenshot_service: DashboardScreenshotService, settings: Settings):
        self._repos = repositories
        self._screenshot_service = screenshot_service
        self._settings = settings

    async def start(self):
        # Инициализация бота
        bot = Bot(token=self._settings.telegram_bot_token, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
        dp = Dispatcher()

        # Создание middleware
        repo_middleware = RepoMiddleware(self._repos)
        screenshot_middleware = DashboardScreenshotMiddleware(self._screenshot_service)
        user_middleware = UserMiddleware()

        # Подключение RepoMiddleware для инжекта repositories
        dp.message.outer_middleware(repo_middleware)
        dp.callback_query.outer_middleware(repo_middleware)

        # Подключение DashboardScreenshotService для инжекта DashboardScreenshotService
        dp.message.outer_middleware(screenshot_middleware)
        dp.callback_query.outer_middleware(screenshot_middleware)

        # Подключение UserMiddleware для инжекта информации о пользователе
        dp.message.outer_middleware(user_middleware)
        dp.callback_query.outer_middleware(user_middleware)

        # Инициализация роутеров
        admin_router = create_admin_router()
        client_router = create_client_router()

        # Создание фильтров для роутеров
        admin_filter = RoleFilter("admin")
        client_filter = RoleFilter("client")

        # Настройка фильтра для админского роутера
        admin_router.message.filter(admin_filter)
        admin_router.callback_query.filter(admin_filter)

        # Настройка фильтра для клиентского роутера
        client_router.message.filter(client_filter)
        client_router.callback_query.filter(client_filter)

        dp.include_router(admin_router)
        dp.include_router(client_router)

        try:
            print("Запускаю пуллинг...")
            await dp.start_polling(bot)

        except Exception as e:
            print(f"Ошибка во время выполнения пуллинга {e}")
            await bot.session.close()