from src.models import RetentionCase
from src.repositories import Database


class RetentionCaseRepository:
    def __init__(self, database: Database):
        self._database = database

    async def create_table(self):
        await self._database.execute("""
            CREATE TABLE IF NOT EXISTS retention_cases (
                case_id INT PRIMARY KEY AUTO_INCREMENT,
                contract_id VARCHAR(32) NOT NULL,
            
                initial_reason TEXT,
                proposed_offer_id INT,
            
                assigned_manager_id BIGINT,
            
                created_at DATETIME NOT NULL,
                completed_at DATETIME,
            
                status ENUM('active', 'escalated', 'retained', 'churned'),
            
                FOREIGN KEY (contract_id) REFERENCES Contracts(contract_id),
                FOREIGN KEY (assigned_manager_id) REFERENCES Users(telegram_id),
                FOREIGN KEY (proposed_offer_id) REFERENCES Offers(offer_id)
            )
        """)

    async def insert(self, retention_case: RetentionCase):
        params = (
            retention_case.contract_id,
            retention_case.initial_reason,
            retention_case.proposed_offer_id,
            retention_case.assigned_manager_id,
            retention_case.created_at,
            retention_case.completed_at,
            retention_case.status
        )

        return await self._database.execute("""
            INSERT INTO retention_cases (
                contract_id,
                initial_reason,
                proposed_offer_id,
                assigned_manager_id,
                created_at,
                completed_at,
                status
            ) VALUE (%s, %s, %s, %s, %s, %s, %s)
        """, *params)

    async def update(self, c: RetentionCase):
        await self._database.execute("""
            UPDATE retention_cases SET 
                    contract_id = %s,
                    initial_reason = %s, 
                    proposed_offer_id = %s, 
                    assigned_manager_id = %s, 
                    created_at = %s, 
                    completed_at = %s, 
                    status = %s
                WHERE case_id = %s
        """,
            c.contract_id, c.initial_reason, c.proposed_offer_id,
            c.assigned_manager_id, c.created_at, c.completed_at, c.status, c.case_id
        )

    async def remove(self, retention_case_id: int):
        await self._database.execute("""
            DELETE FROM retention_cases WHERE case_id = %s
        """, retention_case_id)

    async def get_one(self, retention_case_id: int):
        case_tuple = await self._database.select_one("""
            SELECT * FROM retention_cases WHERE case_id = %s
        """, retention_case_id)

        return None if case_tuple is None else RetentionCase(*case_tuple.values())

    async def get_active_case_for_contract(self, contract_id: int):
        case_tuple = await self._database.select_one("""
            SELECT * FROM retention_cases WHERE contract_id = %s AND status IN ('active', 'escalated')
        """, contract_id)

        return None if case_tuple is None else RetentionCase(*case_tuple.values())

    async def get_all(self):
        case_tuples = await self._database.select_all("""
            SELECT * FROM retention_cases
        """)

        return [RetentionCase(*case_tuple.values()) for case_tuple in case_tuples]

    async def get_all_escalated(self):
        case_tuples = await self._database.select_all("""
            SELECT * FROM retention_cases WHERE status = 'escalated'
        """)

        return [RetentionCase(*case_tuple.values()) for case_tuple in case_tuples]