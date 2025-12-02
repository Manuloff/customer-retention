from os import getenv

from dotenv import load_dotenv


class Settings:
    def __init__(self):
        load_dotenv()

        # Токен телеграмм бота
        self.telegram_bot_token = getenv('TELEGRAM_BOT_TOKEN')

        # Настройки подключения к MySQL
        self.db_host = getenv('DB_HOST')
        self.db_user = getenv('DB_USER')
        self.db_password = getenv('DB_PASSWORD')
        self.db_name = getenv('DB_NAME')

        # Настройки сервера Dash
        self.dash_host = getenv('DASH_HOST')
        self.dash_port = getenv('DASH_PORT')

        # URL, где запущен Дашборд.
        self.dashboard_url = getenv('DASHBOARD_URL')