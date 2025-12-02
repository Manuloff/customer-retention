from src.repositories import Database

from src.repositories.contract_repository import ContractRepository
from src.repositories.offer_repository import OfferRepository
from src.repositories.retention_case_repository import RetentionCaseRepository
from src.repositories.user_repository import UserRepository


class Repositories:
    def __init__(self, database: Database):
        self.database = database
        self.users = UserRepository(database)
        self.offers = OfferRepository(database)
        self.contracts = ContractRepository(database)
        self.cases = RetentionCaseRepository(database)