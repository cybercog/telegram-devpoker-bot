from app.discussion_vote import DiscussionVote
from app.estimation_vote import EstimationVote
import collections
import json

CARD_DECK_LAYOUT = [
    ["0", "0.5", "1", "2", "3", "4"],
    ["5", "6", "7", "8", "9", "10"],
    ["12", "18", "24", "30"],
    ["✂️", "♾️", "❓", "☕"],
]


class Game:
    PHASE_DISCUSSION = "discussion"
    PHASE_ESTIMATION = "estimation"
    PHASE_RESOLUTION = "resolution"

    OPERATION_START_ESTIMATION = "start_estimation"
    OPERATION_END_ESTIMATION = "end_estimation"
    OPERATION_CLEAR_VOTES = "clear_votes"
    OPERATION_RE_ESTIMATE = "re_estimate"

    def __init__(self, chat_id, topic_message_id, initiator, topic):
        self.chat_id = chat_id
        self.topic_message_id = topic_message_id
        self.game_message_id = 0
        self.phase = self.PHASE_DISCUSSION
        self.initiator = initiator
        self.topic = topic
        self.estimation_votes = collections.defaultdict(EstimationVote)
        self.discussion_votes = collections.defaultdict(DiscussionVote)

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

    def add_discussion_vote(self, initiator, vote):
        self.discussion_votes[self._initiator_str(initiator)].set(vote)

    def add_estimation_vote(self, initiator, vote):
        self.estimation_votes[self._initiator_str(initiator)].set(vote)

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

        result += self.topic

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

    def render_discussion_votes_text(self):
        result = ""

        votes_count = len(self.discussion_votes)

        if votes_count > 0:
            result += "Votes ({}):".format(votes_count)
            result += "\n"
            result += join(
                "{} {}".format(
                    discussion_vote.icon,
                    user_id,
                )
                for user_id, discussion_vote in sorted(self.discussion_votes.items())
            )

        return result

    def render_estimation_votes_text(self):
        result = ""

        votes_count = len(self.estimation_votes)

        if votes_count > 0:
            result += "Votes ({}):".format(votes_count)
            result += "\n"
            result += join(
                "{} {}".format(
                    estimation_vote.vote if self.phase == self.PHASE_RESOLUTION else estimation_vote.masked,
                    user_id,
                )
                for user_id, estimation_vote in sorted(self.estimation_votes.items())
            )

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
            "callback_data": "discussion-vote-click-{}-{}".format(self.topic_message_id, DiscussionVote.VOTE_TO_ESTIMATE),
        }

    def get_need_discuss_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "⁉️ Discuss",
            "callback_data": "discussion-vote-click-{}-{}".format(self.topic_message_id, DiscussionVote.VOTE_NEED_DISCUSS),
        }

    def get_estimation_vote_button(self, vote):
        return {
            "type": "InlineKeyboardButton",
            "text": vote,
            "callback_data": "estimation-vote-click-{}-{}".format(self.topic_message_id, vote),
        }

    def get_start_estimation_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "Start estimation",
            "callback_data": "{}-click-{}".format(self.OPERATION_START_ESTIMATION, self.topic_message_id),
        }

    def get_clear_votes_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "Clear votes",
            "callback_data": "{}-click-{}".format(self.OPERATION_CLEAR_VOTES, self.topic_message_id),
        }

    def get_re_vote_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "Re-estimate",
            "callback_data": "{}-click-{}".format(self.OPERATION_RE_ESTIMATE, self.topic_message_id),
        }

    def get_end_game_button(self):
        return {
            "type": "InlineKeyboardButton",
            "text": "End estimation",
            "callback_data": "{}-click-{}".format(self.OPERATION_END_ESTIMATION, self.topic_message_id),
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

    @staticmethod
    def _initiator_str(initiator: dict) -> str:
        return "@{} ({})".format(
            initiator.get("username") or initiator.get("id"),
            initiator["first_name"]
        )

    @staticmethod
    def votes_to_json(votes):
        return {
            user_id: vote.to_dict() for user_id, vote in votes.items()
        }

    def to_dict(self):
        return {
            "game_message_id": self.game_message_id,
            "phase": self.phase,
            "initiator": self.initiator,
            "topic": self.topic,
            "discussion_votes": self.votes_to_json(self.discussion_votes),
            "estimation_votes": self.votes_to_json(self.estimation_votes),
        }

    @classmethod
    def from_dict(cls, chat_id, topic_message_id, dict):
        result = cls(chat_id, topic_message_id, dict["initiator"], dict["topic"])
        result.game_message_id = dict["game_message_id"]
        result.phase = dict["phase"]

        for user_id, discussion_vote in dict["discussion_votes"].items():
            result.discussion_votes[user_id] = DiscussionVote.from_dict(discussion_vote)

        for user_id, estimation_vote in dict["estimation_votes"].items():
            result.estimation_votes[user_id] = EstimationVote.from_dict(estimation_vote)

        return result
