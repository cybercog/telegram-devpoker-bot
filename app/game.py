from app.telegram_user import TelegramUser


class Game:
    STATUS_STARTED = "started"
    STATUS_ENDED = "ended"

    def __init__(self, chat_id: int, facilitator_message_id: int, name: str, facilitator: TelegramUser):
        self.id = None
        self.system_message_id = None
        self.chat_id = chat_id
        self.facilitator_message_id = facilitator_message_id
        self.status = self.STATUS_STARTED
        self.name = name
        self.facilitator = facilitator

    def render_system_message(self):
        return {
            "text": self.render_system_message_text(),
        }

    def render_results_system_message(self, game_statistics):
        return {
            "text": self.render_results_system_message_text(game_statistics),
        }

    def render_system_message_text(self) -> str:
        result = ""

        result += self.render_name_text()
        result += "\n"
        result += self.render_facilitator_text()

        return result

    def render_results_system_message_text(self, game_statistics) -> str:
        result = ""

        result += self.render_name_text()
        result += "\n"
        result += self.render_facilitator_text()
        result += "\n"
        result += "\n"
        result += self.render_statistics_text(game_statistics)

        return result

    def render_facilitator_text(self) -> str:
        return "Facilitator: {}".format(self.facilitator.to_string())

    def render_name_text(self) -> str:
        if self.status == self.STATUS_STARTED:
            return "Planning poker started: " + self.name
        elif self.status == self.STATUS_ENDED:
            return "Planning poker ended: " + self.name
        else:
            return ""

    def render_statistics_text(self, game_statistics) -> str:
        result = ""

        result += "Estimated topics count: {}".format(game_statistics["estimated_game_sessions_count"])

        return result


    def to_dict(self):
        return {
            "facilitator": self.facilitator.to_dict(),
        }

    @classmethod
    def from_dict(cls, chat_id: int, facilitator_message_id: int, name: str, facilitator: TelegramUser):
        return cls(
            chat_id,
            facilitator_message_id,
            name,
            facilitator,
        )
