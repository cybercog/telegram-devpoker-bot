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


class DiscussionVote:
    VOTE_TO_ESTIMATE = "to_estimate"
    VOTE_NEED_DISCUSS = "need_discuss"

    def __init__(self):
        self.vote = ""

    def set(self, vote):
        self.vote = vote

    @property
    def icon(self):
        if self.vote in self.VOTE_TO_ESTIMATE:
            return "👍"
        elif self.vote in self.VOTE_NEED_DISCUSS:
            return "⁉️"

    def to_dict(self):
        return {
            "vote": self.vote,
        }

    @classmethod
    def from_dict(cls, dict):
        result = cls()
        result.vote = dict["vote"]

        return result


class EstimationVote:
    def __init__(self):
        self.vote = ""
        self.version = -1

    def set(self, vote):
        self.vote = vote
        self.version += 1

    @property
    def masked(self):
        return CARD_SUITES[self.version % len(CARD_SUITES)]

    def to_dict(self):
        return {
            "vote": self.vote,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, dict):
        result = cls()
        result.vote = dict["vote"]
        result.version = dict["version"]

        return result


class Game:
    PHASE_DISCUSSION = "discussion"
    PHASE_ESTIMATION = "estimation"
    PHASE_RESOLUTION = "resolution"

    OPERATION_START_ESTIMATION = "start_estimation"
    OPERATION_END_ESTIMATION = "end_estimation"
    OPERATION_CLEAR_VOTES = "clear_votes"
    OPERATION_RE_ESTIMATE = "re_estimate"

    def __init__(self, chat_id, message_id, initiator, text):
        self.chat_id = chat_id
        self.message_id = message_id
        self.initiator = initiator
        self.text = text
        self.reply_message_id = 0
        self.estimation_votes = collections.defaultdict(EstimationVote)
        self.discussion_votes = collections.defaultdict(DiscussionVote)
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
        result = ""

        if self.discussion_votes:
            votes_string = "\n".join(
                "{:3s} {}".format(
                    vote.icon, user_id
                )
                for user_id, vote in sorted(self.discussion_votes.items())
            )
            votes_count = len(self.discussion_votes)
            result += "Votes ({}):\n{}".format(votes_count, votes_string)

        return result

    def render_estimation_votes_text(self):
        result = ""

        if self.estimation_votes:
            votes_string = "\n".join(
                "{:3s} {}".format(
                    vote.vote if self.phase == self.PHASE_RESOLUTION else vote.masked, user_id
                )
                for user_id, vote in sorted(self.estimation_votes.items())
            )
            votes_count = len(self.estimation_votes)
            result += "Votes ({}):\n{}".format(votes_count, votes_string)

        return result

    def get_send_kwargs(self):
        return {
            "text": self.render_message_text(),
            "reply_markup": json.dumps(self.get_markup()),
        }

    def get_to_estimate_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "👍 To estimate",
            "callback_data": "discussion-vote-click-{}-{}".format(self.message_id, DiscussionVote.VOTE_TO_ESTIMATE),
        }

    def get_need_discuss_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "⁉️ Discuss",
            "callback_data": "discussion-vote-click-{}-{}".format(self.message_id, DiscussionVote.VOTE_NEED_DISCUSS),
        }

    def get_estimation_vote_button(self, vote):
        return {
            "type": "InlineKeyboardButton",
            "text": vote,
            "callback_data": "estimation-vote-click-{}-{}".format(self.message_id, vote),
        }

    def get_start_estimation_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "Start estimation",
            "callback_data": "{}-click-{}".format(self.OPERATION_START_ESTIMATION, self.message_id),
        }

    def get_clear_votes_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "Clear votes",
            "callback_data": "{}-click-{}".format(self.OPERATION_CLEAR_VOTES, self.message_id),
        }

    def get_re_vote_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "Re-estimate",
            "callback_data": "{}-click-{}".format(self.OPERATION_RE_ESTIMATE, self.message_id),
        }

    def get_end_game_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "End estimation",
            "callback_data": "{}-click-{}".format(self.OPERATION_END_ESTIMATION, self.message_id),
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
            for votes_layout_row in CARD_DECK_LAYOUT:
                vote_buttons_row = []
                for vote in votes_layout_row:
                    vote_buttons_row.append(self.get_estimation_vote_button(vote))
                layout_rows.append(vote_buttons_row)

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
            "discussion_votes": {user_id: discussion_vote.to_dict() for user_id, discussion_vote in self.discussion_votes.items()},
            "estimation_votes": {user_id: estimation_vote.to_dict() for user_id, estimation_vote in self.estimation_votes.items()},
        }

    @classmethod
    def from_dict(cls, chat_id, message_id, dict):
        result = cls(chat_id, message_id, dict["initiator"], dict["text"])
        result.reply_message_id = dict["reply_message_id"]
        result.phase = dict["phase"]

        for user_id, discussion_vote in dict["discussion_votes"].items():
            result.discussion_votes[user_id] = DiscussionVote.from_dict(discussion_vote)

        for user_id, estimation_vote in dict["estimation_votes"].items():
            result.estimation_votes[user_id] = EstimationVote.from_dict(estimation_vote)

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
            (game.chat_id, game.message_id, json.dumps(game.to_dict()))
        )
        await self._db.commit()
