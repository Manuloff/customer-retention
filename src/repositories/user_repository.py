from src.models import User
from src.repositories.database import Database

class UserRepository:
    def __init__(self, database: Database):
        self._database = database

    async def create_table(self):
        await self._database.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id BIGINT PRIMARY KEY,
                role ENUM('client', 'admin')
            )
        """)

    async def insert(self, user: User):
        await self._database.execute("""
            INSERT INTO users (telegram_id, role) VALUE (%s, %s)
        """, *user.tuple())

    async def get_one(self, telegram_id: int):
        user_tuple = await self._database.select_one("""
            SELECT * FROM users WHERE telegram_id = %s
        """, telegram_id)

        return None if user_tuple is None else User(*user_tuple.values())

    async def get_free_admins(self):
        user_tuples = await self._database.select_all("""
            SELECT * FROM users WHERE role = 'admin'
        """)

        return [User(*user_tuple.values()) for user_tuple in user_tuples]

    async def get_all(self):
        user_tuples = await self._database.select_all("""
            SELECT * FROM users
        """)

        return [User(*user_tuple.values()) for user_tuple in user_tuples]