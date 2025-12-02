class User:
    def __init__(
            self,
            telegram_id: int,
            role: str,
    ):
        self.telegram_id = telegram_id
        self.role = role

    def tuple(self):
        return (
            self.telegram_id,
            self.role
        )