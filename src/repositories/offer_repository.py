from src.models import Offer
from src.repositories import Database

class OfferRepository:
    def __init__(self, database: Database):
        self._database = database

    async def create_table(self):
        await self._database.execute("""
            CREATE TABLE IF NOT EXISTS offers (
                offer_id INT PRIMARY KEY AUTO_INCREMENT,
                offer_type VARCHAR(50) NOT NULL,
                description TEXT,
                min_profit_threshold DECIMAL(10, 2) NOT NULL,
                cost DECIMAL(10, 2) NOT NULL
            )
        """)

    async def insert(self, offer: Offer):
        await self._database.execute("""
            INSERT INTO offers (offer_type, description, min_profit_threshold, cost)
                VALUE (%s, %s, %s, %s)
        """, offer.offer_type, offer.description, offer.min_profit_threshold, offer.cost)

    async def update(self, offer: Offer):
        await self._database.execute("""
            UPDATE offers SET 
                    offer_type = %s, 
                    description = %s, 
                    min_profit_threshold = %s, 
                    cost = %s
                WHERE offer_id = %s
        """, offer.offer_type, offer.description, offer.min_profit_threshold, offer.cost, offer.offer_id)

    async def remove(self, offer_id: int):
        await self._database.execute("""
            DELETE FROM offers WHERE offer_id = %s
        """, offer_id)

    async def get_all(self):
        offer_tuples = await self._database.select_all("""
            SELECT * FROM offers
        """)

        return [Offer(*offer_tuple.values()) for offer_tuple in offer_tuples]

    async def get_one(self, offer_id: int):
        offer_tuple = await self._database.select_one("""
            SELECT * FROM offers WHERE offer_id = %s
        """, offer_id)

        return None if offer_tuple is None else Offer(*offer_tuple.values())

    async def get_suitable_offers(self, client_monthly_profit: float):
        offer_tuples = await self._database.select_all("""
            SELECT * FROM offers WHERE min_profit_threshold <= %s
        """, client_monthly_profit)

        return [Offer(*offer_tuple.values()) for offer_tuple in offer_tuples]