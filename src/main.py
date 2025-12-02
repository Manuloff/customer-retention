import asyncio
import threading

from src.config import Settings
from src.dashboard.dash_app import init_dashboard
from src.repositories import Database, Repositories
from src.services import DashboardScreenshotService
from src.telegram.tg_app import TelegramApp


async def main():
    settings = Settings()

    database = Database(settings)
    repositories = Repositories(database)

    screenshot_service = DashboardScreenshotService(settings.dashboard_url)

    async with database:
        await repositories.users.create_table()
        await repositories.contracts.create_table()
        await repositories.offers.create_table()
        await repositories.cases.create_table()

    dash_thread = threading.Thread(
        target=init_dashboard,
        args=(repositories, settings),
        daemon=True
    )
    dash_thread.start()

    await TelegramApp(repositories, screenshot_service, settings).start()


if __name__ == "__main__":
    asyncio.run(main())