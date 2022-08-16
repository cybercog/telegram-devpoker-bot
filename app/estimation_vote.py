class EstimationVote:
    CARD_SUITES = [
        "♥️", "♠️", "♦️", "♣️",
    ]

    def __init__(self):
        self.vote = ""
        self.version = -1

    def set(self, vote):
        self.vote = vote
        self.version += 1

    @property
    def masked(self):
        return self.CARD_SUITES[self.version % len(self.CARD_SUITES)]

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