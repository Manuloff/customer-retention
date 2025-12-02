class Offer:
    def __init__(
            self,
            offer_id: int,
            offer_type: str,
            description: str,
            min_profit_threshold: float,
            cost: float
    ):
        self.offer_id = offer_id
        self.offer_type = offer_type

        self.description = description

        self.min_profit_threshold = min_profit_threshold

        self.cost = cost

    def tuple(self):
        return (
            self.offer_id,
            self.offer_type,
            self.description,
            self.min_profit_threshold,
            self.cost
        )