from datetime import datetime
from typing import Optional

class RetentionCase:
    def __init__(
            self,
            case_id: int,
            contract_id: str,
            initial_reason: str,
            proposed_offer_id: Optional[int],
            assigned_manager_id: Optional[int],
            created_at: datetime,
            completed_at: Optional[datetime],
            status: str
    ):
        self.case_id = case_id
        self.contract_id = contract_id

        self.initial_reason = initial_reason
        self.proposed_offer_id = proposed_offer_id

        self.assigned_manager_id = assigned_manager_id

        self.created_at = created_at
        self.completed_at = completed_at

        self.status = status

    def tuple(self):
        return (
            self.case_id,
            self.contract_id,
            self.initial_reason,
            self.proposed_offer_id,
            self.assigned_manager_id,
            self.created_at,
            self.completed_at,
            self.status
        )