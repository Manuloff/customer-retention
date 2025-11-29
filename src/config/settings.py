from os import getenv
from dotenv import load_dotenv

class Settings:
    def __init__(self):
        # Загружаем переменные окружения из файла .env
        load_dotenv()

        # --- Настройки Telegram-бота ---
        self.TELEGRAM_BOT_TOKEN = getenv('TELEGRAM_BOT_TOKEN')

        # --- Настройки MySQL Базы Данных ---
        self.DB_HOST = getenv('DB_HOST')
        self.DB_USER = getenv('DB_USER')
        self.DB_PASSWORD = getenv('DB_PASSWORD')
        self.DB_NAME = getenv('DB_NAME')

        # URL, где запущен Dash-дашборд. Нужен для Selenium.
        self.DASHBOARD_URL = getenv('DASHBOARD_URL', 'http://127.0.0.1:8050')