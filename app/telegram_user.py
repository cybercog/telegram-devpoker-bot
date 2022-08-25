class TelegramUser:
    def __init__(self, id: int, is_bot: bool, first_name: str, last_name: str, username: str):
        self.id = id
        self.is_bot = is_bot
        self.first_name = first_name
        self.last_name = last_name
        self.username = username

    def to_string(self) -> str:
        return "@{} ({})".format(
            self.username or self.id,
            "{} {}".format(self.first_name, self.last_name or "").strip()
        )

    def to_dict(self):
        return {
            "id": self.id,
            "is_bot": self.is_bot,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "username": self.username,
        }

    @classmethod
    def from_dict(cls, dict):
        return cls(
            dict.get("id"),
            dict.get("is_bot"),
            dict.get("first_name"),
            dict.get("last_name"),
            dict.get("username"),
        )
