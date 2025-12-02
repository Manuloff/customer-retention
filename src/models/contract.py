class Contract:
    def __init__(
            self,
            contract_id: str,
            client_telegram_id: int,
            last_name: str,
            first_name: str,
            middle_name: str,
            email: str,
            phone: str,
            can_be_retained: bool,
            monthly_profit: float,
            active: bool,
    ):
        self.contract_id = contract_id
        self.client_telegram_id = client_telegram_id

        self.last_name = last_name
        self.first_name = first_name
        self.middle_name = middle_name

        self.email = email
        self.phone = phone

        self.can_be_retained = can_be_retained

        self.monthly_profit = monthly_profit
        self.active = active

    def tuple(self):
        return (
            self.contract_id,
            self.client_telegram_id,
            self.last_name,
            self.first_name,
            self.middle_name,
            self.email,
            self.phone,
            self.can_be_retained,
            self.monthly_profit,
            self.active
        )