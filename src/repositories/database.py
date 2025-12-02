import warnings
from typing import Optional, List

import aiomysql
from aiomysql import Connection, DictCursor

from src.config.settings import Settings

warnings.filterwarnings("ignore", category=Warning, message="Table '.*' already exists")

class Database:
    def __init__(self, settings: Settings):
        self._host = settings.db_host
        self._user = settings.db_user
        self._password = settings.db_password
        self._db_name = settings.db_name

        self._conn: Optional[Connection] = None

    async def __aenter__(self):

        try:
            self._conn = await aiomysql.connect(
                host=self._host,
                user=self._user,
                password=self._password,
                db=self._db_name,
                autocommit=True,
                charset='utf8mb4'
            )
            return self
        except Exception as e:
            print(f"Ошибка при подключении к MySQL: {e}")
            raise

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._conn:
            self._conn.close()

    async def execute(self, query: str, *params):
        if not self._conn:
            raise ConnectionError("Соединение с базой данных не установлено")

        async with self._conn.cursor() as cursor:
            await cursor.execute(query, params)
            return cursor.lastrowid

    async def select_one(self, query: str, *params) -> Optional[dict]:
        if not self._conn:
            raise ConnectionError("Соединение с базой данных не установлено")

        async with self._conn.cursor(DictCursor) as cursor:
            await cursor.execute(query, params)
            return await cursor.fetchone()

    async def select_all(self, query: str, *params) -> List[dict]:
        if not self._conn:
            raise ConnectionError("Соединение с базой данных не установлено")

        async with self._conn.cursor(DictCursor) as cursor:
            await cursor.execute(query, params)
            return await cursor.fetchall()