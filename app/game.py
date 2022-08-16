import aiosqlite
import collections
import json

CARD_SUITES = [
    "♥️", "♠️", "♦️", "♣️",
]

CARD_DECK_LAYOUT = [
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
    def from_dict(cls, dict):
        result = cls()
        result.point = dict["point"]
        result.version = dict["version"]

        return result


class LobbyVote:
    def __init__(self):
        self.status = ""

    def set(self, status):
        self.status = status

    @property
    def icon(self):
        if self.status in "to_estimate":
            return "👍"
        elif self.status in "need_discuss":
            return "⁉️"

    def to_dict(self):
        return {
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, dict):
        result = cls()
        result.status = dict["status"]

        return result


class Game:
    PHASE_DISCUSSION = "discussion"
    PHASE_ESTIMATION = "estimation"
    PHASE_RESOLUTION = "resolution"

    OPERATION_START_ESTIMATION = "start_estimation"
    OPERATION_END_ESTIMATION = "end_estimation"
    OPERATION_CLEAR_VOTES = "clear_votes"
    OPERATION_RE_ESTIMATE = "re_estimate"

    def __init__(self, chat_id, vote_id, initiator, text):
        self.chat_id = chat_id
        self.vote_id = vote_id
        self.initiator = initiator
        self.text = text
        self.reply_message_id = 0
        self.estimation_votes = collections.defaultdict(Vote)
        self.discussion_votes = collections.defaultdict(LobbyVote)
        self.phase = self.PHASE_DISCUSSION

    def add_estimation_vote(self, initiator, vote):
        self.estimation_votes[self._initiator_str(initiator)].set(vote)

    def add_discussion_vote(self, initiator, vote):
        self.discussion_votes[self._initiator_str(initiator)].set(vote)

    def render_message_text(self):
        result = ""

        result += self.render_initiator_text()
        result += "\n"
        result += self.render_topic_text()
        result += "\n"
        result += "\n"
        result += self.render_votes_text()

        return result

    def render_topic_text(self):
        result = ""

        if self.text in "":
            return result

        if self.phase in self.PHASE_DISCUSSION:
            result += "Discussion for: "
        elif self.phase in self.PHASE_ESTIMATION:
            result += "Estimation for: "
        elif self.phase in self.PHASE_RESOLUTION:
            result += "Resolution for: "

        result += self.text

        return result

    def render_initiator_text(self):
        return "Initiator: {}".format(self._initiator_str(self.initiator))

    def render_votes_text(self):
        if self.phase in self.PHASE_DISCUSSION:
            return self.render_discussion_votes_text()
        elif self.phase in self.PHASE_ESTIMATION:
            return self.render_estimation_votes_text()
        elif self.phase in self.PHASE_RESOLUTION:
            return self.render_estimation_votes_text()
        else:
            return ""

    def render_discussion_votes_text(self):
        votes_count = len(self.discussion_votes)

        result = ""

        if self.discussion_votes:
            votes_string = "\n".join(
                "{:3s} {}".format(
                    vote.icon, user_id
                )
                for user_id, vote in sorted(self.discussion_votes.items())
            )
            result += "Votes ({}):\n{}".format(votes_count, votes_string)

        return result

    def render_estimation_votes_text(self):
        votes_count = len(self.estimation_votes)

        result = ""

        if self.estimation_votes:
            votes_string = "\n".join(
                "{:3s} {}".format(
                    vote.point if self.phase == self.PHASE_RESOLUTION else vote.masked, user_id
                )
                for user_id, vote in sorted(self.estimation_votes.items())
            )
            result += "Votes ({}):\n{}".format(votes_count, votes_string)

        return result

    def get_send_kwargs(self):
        return {
            "text": self.render_message_text(),
            "reply_markup": json.dumps(self.get_markup()),
        }

    def get_point_button(self, point):
        return {
            "type": "InlineKeyboardButton",
            "text": point,
            "callback_data": "estimation-vote-click-{}-{}".format(self.vote_id, point),
        }

    def get_to_estimate_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "👍 To estimate",
            "callback_data": "discussion-vote-click-{}-{}".format(self.vote_id, "to_estimate"),
        }

    def get_need_discuss_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "⁉️ Discuss",
            "callback_data": "discussion-vote-click-{}-{}".format(self.vote_id, "need_discuss"),
        }

    def get_start_estimation_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "Start estimation",
            "callback_data": "{}-click-{}".format(self.OPERATION_START_ESTIMATION, self.vote_id),
        }

    def get_clear_votes_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "Clear votes",
            "callback_data": "{}-click-{}".format(self.OPERATION_CLEAR_VOTES, self.vote_id),
        }

    def get_re_vote_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "Re-estimate",
            "callback_data": "{}-click-{}".format(self.OPERATION_RE_ESTIMATE, self.vote_id),
        }

    def get_end_game_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "End estimation",
            "callback_data": "{}-click-{}".format(self.OPERATION_END_ESTIMATION, self.vote_id),
        }

    def get_markup(self):
        layout_rows = []

        if self.phase in self.PHASE_DISCUSSION:
            layout_rows.append(
                [
                    self.get_to_estimate_button(),
                    self.get_need_discuss_button(),
                ]
            )
            layout_rows.append(
                [
                    self.get_start_estimation_button(),
                ]
            )
        elif self.phase in self.PHASE_ESTIMATION:
            for points_layout_row in CARD_DECK_LAYOUT:
                points_buttons_row = []
                for point in points_layout_row:
                    points_buttons_row.append(self.get_point_button(point))
                layout_rows.append(points_buttons_row)

            layout_rows.append(
                [
                    self.get_clear_votes_button(),
                    self.get_end_game_button(),
                ]
            )
        elif self.phase in self.PHASE_RESOLUTION:
            layout_rows.append(
                [
                    self.get_re_vote_button(),
                ]
            )

        return {
            "type": "InlineKeyboardMarkup",
            "inline_keyboard": layout_rows,
        }

    def start_estimation(self):
        self.phase = self.PHASE_ESTIMATION

    def end_estimation(self):
        self.phase = self.PHASE_RESOLUTION

    def clear_votes(self):
        self.estimation_votes.clear()
        self.phase = self.PHASE_ESTIMATION

    def re_estimate(self):
        self.estimation_votes.clear()
        self.phase = self.PHASE_ESTIMATION

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
            "votes": {user_id: vote.to_dict() for user_id, vote in self.estimation_votes.items()},
            "lobby_votes": {user_id: lobby_vote.to_dict() for user_id, lobby_vote in self.discussion_votes.items()},
        }

    @classmethod
    def from_dict(cls, chat_id, vote_id, dict):
        result = cls(chat_id, vote_id, dict["initiator"], dict["text"])
        result.reply_message_id = dict["reply_message_id"]
        result.phase = dict["phase"]

        for user_id, lobby_vote in dict["lobby_votes"].items():
            result.discussion_votes[user_id] = LobbyVote.from_dict(lobby_vote)

        for user_id, vote in dict["votes"].items():
            result.estimation_votes[user_id] = Vote.from_dict(vote)

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
        query = "SELECT json_data FROM games WHERE chat_id = ? AND game_id = ?"
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
