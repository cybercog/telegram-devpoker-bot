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
