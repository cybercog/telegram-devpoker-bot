import aiosqlite
import collections
import json

CARD_SUITES = [
    "♥️", "♠️", "♦️", "♣️",
]

POINTS_LAYOUT = [
    ["0", "0.5", "1", "2", "3", "4"],
    ["5", "6", "7", "8", "9", "10"],
    ["12", "18", "24", "30"],
    ["✂️", "♾️", "❓", "☕"],
]


class Vote:
    def __init__(self):
        self.point = ""
        self.version = -1

    def set(self, point):
        self.point = point
        self.version += 1

    @property
    def masked(self):
        return CARD_SUITES[self.version % len(CARD_SUITES)]

    def to_dict(self):
        return {
            "point": self.point,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, dct):
        result = cls()
        result.point = dct["point"]
        result.version = dct["version"]

        return result


class LobbyVote:
    def __init__(self):
        self.status = ""

    def set(self, status):
        self.status = status

    @property
    def icon(self):
        if self.status in "ready":
            return "👍"
        elif self.status in "discuss":
            return "⁉️"

    def to_dict(self):
        return {
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, dct):
        result = cls()
        result.status = dct["status"]

        return result


class Game:
    PHASE_INITIATING = "initiating"
    PHASE_VOTING = "voting"
    PHASE_ENDED = "ended"

    OPERATION_START = "start"
    OPERATION_RESTART = "restart"
    OPERATION_END = "end"
    OPERATION_RE_VOTE = "re-vote"

    def __init__(self, chat_id, vote_id, initiator, text):
        self.chat_id = chat_id
        self.vote_id = vote_id
        self.initiator = initiator
        self.text = text
        self.reply_message_id = 0
        self.votes = collections.defaultdict(Vote)
        self.lobby_votes = collections.defaultdict(LobbyVote)
        self.revealed = False
        self.phase = self.PHASE_INITIATING

    def add_vote(self, initiator, point):
        self.votes[self._initiator_str(initiator)].set(point)

    def add_lobby_vote(self, initiator, status):
        self.lobby_votes[self._initiator_str(initiator)].set(status)

    def render(self):
        result = ""

        result += self.render_summary()
        result += "\n"
        result += self.render_initiator()
        result += "\n"
        result += "\n"
        if self.phase in self.PHASE_INITIATING:
            result += self.render_lobby_votes()
        else:
            result += self.render_votes()

        return result

    def render_summary(self):
        result = ""

        if not self.revealed:
            result += "Vote for:"
        else:
            result += "Results for:"

        result += "\n"
        result += self.text

        return result

    def render_initiator(self):
        return "Initiator: {}".format(self._initiator_str(self.initiator))

    def render_lobby_votes(self):
        lobby_votes_count = len(self.lobby_votes)

        result = ""

        if self.lobby_votes:
            lobby_votes_string = "\n".join(
                "{:3s} {}".format(
                    vote.icon, user_id
                )
                for user_id, vote in sorted(self.lobby_votes.items())
            )
            result += "Ready status ({}):\n{}".format(lobby_votes_count, lobby_votes_string)

        return result

    def render_votes(self):
        votes_count = len(self.votes)

        result = ""

        if self.votes:
            votes_string = "\n".join(
                "{:3s} {}".format(
                    vote.point if self.revealed else vote.masked, user_id
                )
                for user_id, vote in sorted(self.votes.items())
            )
            result += "Votes ({}):\n{}".format(votes_count, votes_string)

        return result

    def get_send_kwargs(self):
        return {
            "text": self.render(),
            "reply_markup": json.dumps(self.get_markup()),
        }

    def get_point_button(self, point):
        return {
            "type": "InlineKeyboardButton",
            "text": point,
            "callback_data": "vote-click-{}-{}".format(self.vote_id, point),
        }

    def get_ready_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "👍 Ready",
            "callback_data": "ready-click-{}-{}".format(self.vote_id, 'ready'),
        }

    def get_discuss_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "⁉️ Discuss",
            "callback_data": "ready-click-{}-{}".format(self.vote_id, 'discuss'),
        }

    def get_start_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "Start",
            "callback_data": "{}-click-{}".format(self.OPERATION_START, self.vote_id),
        }

    def get_restart_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "Restart",
            "callback_data": "{}-click-{}".format(self.OPERATION_RESTART, self.vote_id),
        }

    def get_re_vote_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "Re-vote",
            "callback_data": "{}-click-{}".format(self.OPERATION_RE_VOTE, self.vote_id),
        }

    def get_end_game_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "End game",
            "callback_data": "{}-click-{}".format(self.OPERATION_END, self.vote_id),
        }

    def get_markup(self):
        layout_rows = []

        if self.phase in self.PHASE_INITIATING:
            layout_rows.append(
                [
                    self.get_ready_button(),
                    self.get_discuss_button(),
                ]
            )
            layout_rows.append(
                [
                    self.get_start_button(),
                ]
            )
        elif self.phase in self.PHASE_VOTING:
            for points_layout_row in POINTS_LAYOUT:
                points_buttons_row = []
                for point in points_layout_row:
                    points_buttons_row.append(self.get_point_button(point))
                layout_rows.append(points_buttons_row)

            layout_rows.append(
                [
                    self.get_restart_button(),
                    self.get_end_game_button(),
                ]
            )
        elif self.phase in self.PHASE_ENDED:
            layout_rows.append(
                [
                    self.get_re_vote_button(),
                ]
            )

        return {
            "type": "InlineKeyboardMarkup",
            "inline_keyboard": layout_rows,
        }

    def start(self):
        self.phase = self.PHASE_VOTING

    def restart(self):
        self.votes.clear()
        self.phase = self.PHASE_VOTING

    def end(self):
        self.revealed = True
        self.phase = self.PHASE_ENDED

    def re_vote(self):
        self.votes.clear()
        self.revealed = False
        self.phase = self.PHASE_VOTING

    @staticmethod
    def _initiator_str(initiator: dict) -> str:
        return "@{} ({})".format(
            initiator.get("username") or initiator.get("id"),
            initiator["first_name"]
        )

    def to_dict(self):
        return {
            "initiator": self.initiator,
            "text": self.text,
            "reply_message_id": self.reply_message_id,
            "phase": self.phase,
            "revealed": self.revealed,
            "votes": {user_id: vote.to_dict() for user_id, vote in self.votes.items()},
            "lobby_votes": {user_id: lobby_vote.to_dict() for user_id, lobby_vote in self.lobby_votes.items()},
        }

    @classmethod
    def from_dict(cls, chat_id, vote_id, dct):
        result = cls(chat_id, vote_id, dct["initiator"], dct["text"])
        result.revealed = dct["revealed"]
        result.reply_message_id = dct["reply_message_id"]
        result.phase = dct["phase"]

        for user_id, lobby_vote in dct["lobby_votes"].items():
            result.lobby_votes[user_id] = LobbyVote.from_dict(lobby_vote)

        for user_id, vote in dct["votes"].items():
            result.votes[user_id] = Vote.from_dict(vote)

        return result


class GameRegistry:
    def __init__(self):
        self._db = None

    async def init_db(self, db_path):
        con = aiosqlite.connect(db_path)
        con.daemon = True
        self._db = await con
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS games (
                chat_id, game_id, 
                json_data,
                PRIMARY KEY (chat_id, game_id)
            )
        """)

    def new_game(self, chat_id, incoming_message_id: str, initiator: dict, text: str):
        return Game(chat_id, incoming_message_id, initiator, text)

    async def get_game(self, chat_id, incoming_message_id: str) -> Game:
        query = 'SELECT json_data FROM games WHERE chat_id = ? AND game_id = ?'
        async with self._db.execute(query, (chat_id, incoming_message_id)) as cursor:
            result = await cursor.fetchone()
            if not result:
                return None
            return Game.from_dict(chat_id, incoming_message_id, json.loads(result[0]))

    async def save_game(self, game: Game):
        await self._db.execute(
            "INSERT OR REPLACE INTO games VALUES (?, ?, ?)",
            (game.chat_id, game.vote_id, json.dumps(game.to_dict()))
        )
        await self._db.commit()
