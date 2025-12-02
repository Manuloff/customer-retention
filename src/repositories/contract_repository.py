from src.models import Contract
from src.repositories import Database


class ContractRepository:
    def __init__(self, database: Database):
        self._database = database

    async def create_table(self):
        await self._database.execute("""
            CREATE TABLE IF NOT EXISTS contracts (
                contract_id VARCHAR(32) PRIMARY KEY,
                client_telegram_id BIGINT NOT NULL,
                last_name VARCHAR(50),
                first_name VARCHAR(50),
                middle_name VARCHAR(50),
                email VARCHAR(100),
                phone VARCHAR(20),
                can_be_retained BOOLEAN NOT NULL,
                monthly_profit DECIMAL(10, 2) NOT NULL,
                active BOOLEAN DEFAULT TRUE
            )
        """)


    async def remove(self, contract_id):
        await self._database.execute("""
            DELETE FROM contracts WHERE contract_id=%s
        """, contract_id)

    async def insert(self, contract: Contract):
        await self._database.execute("""
            INSERT INTO contracts (
                contract_id,
                client_telegram_id,
                last_name, first_name, middle_name,
                email, phone,
                can_be_retained,
                monthly_profit,
                active
            ) VALUE (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)  
        """, *contract.tuple())

    async def update(self, c: Contract):
        await self._database.execute("""
            UPDATE contracts SET
                    client_telegram_id = %s,
                    last_name = %s,
                    first_name = %s,
                    middle_name = %s,
                    email = %s,
                    phone = %s,
                    can_be_retained = %s,
                    monthly_profit = %s,
                    active = %s
                WHERE contract_id = %s
        """, c.client_telegram_id, c.last_name, c.first_name, c.middle_name, c.email, c.phone, c.can_be_retained, c.monthly_profit, c.active, c.contract_id)

    async def get_one(self, contract_id: str):
        contract_tuple = await self._database.select_one("""
            SELECT * FROM contracts WHERE contract_id = %s
        """, contract_id)

        return None if contract_tuple is None else Contract(*contract_tuple.values())

    async def get_by_client_telegram_id(self, client_telegram_id):
        contract_tuple = await self._database.select_one("""
            SELECT * FROM contracts WHERE client_telegram_id = %s
        """, client_telegram_id)

        return None if contract_tuple is None else Contract(*contract_tuple.values())

    async def get_all(self):
        contract_tuples = await self._database.select_all("""
            SELECT * FROM contracts              
        """)

        return [Contract(*contract_tuple.values()) for contract_tuple in contract_tuples]