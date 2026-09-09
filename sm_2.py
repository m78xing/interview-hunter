from datetime import datetime, timezone, timedelta
from typing import Any
from copy import deepcopy
from math import ceil


class Card:
    card_id: int
    n: int
    EF: float
    I: int
    due: datetime
    needs_extra_review: bool

    def __init__(
        self,
        card_id: int | None = None,
        n: int = 0,
        EF: float = 2.5,
        I: int = 0,
        due: datetime | None = None,
        needs_extra_review: bool = False,
    ) -> None:
        if card_id is None:
            card_id = int(datetime.now(timezone.utc).timestamp() * 1000)
        self.card_id = card_id

        self.n = n
        self.EF = EF
        self.I = I

        if due is None:
            due = datetime.now(timezone.utc)
        self.due = due

        self.needs_extra_review = needs_extra_review

    def to_dict(self) -> dict[str, int | float | str | bool]:
        return_dict: dict[str, int | float | str | bool] = {
            "card_id": self.card_id,
            "n": self.n,
            "EF": self.EF,
            "I": self.I,
            "due": self.due.isoformat(),
            "needs_extra_review": self.needs_extra_review,
        }

        return return_dict

    @staticmethod
    def from_dict(source_dict: dict[str, Any]) -> "Card":
        card_id = int(source_dict["card_id"])
        n = int(source_dict["n"])
        EF = float(source_dict["EF"])
        I = int(source_dict["I"])
        due = datetime.fromisoformat(source_dict["due"])
        needs_extra_review = bool(source_dict["needs_extra_review"])

        return Card(
            card_id=card_id,
            n=n,
            EF=EF,
            I=I,
            due=due,
            needs_extra_review=needs_extra_review,
        )


class ReviewLog:
    card: Card
    rating: int
    review_datetime: datetime
    review_duration: int | None

    def __init__(
        self,
        card: Card,
        rating: int,
        review_datetime: datetime,
        review_duration: int | None = None,
    ) -> None:
        self.card = deepcopy(card)
        self.rating = rating
        self.review_datetime = review_datetime
        self.review_duration = review_duration

    def to_dict(self) -> dict[str, dict | int | str | None]:
        return_dict: dict[str, dict | int | str | None] = {
            "card": self.card.to_dict(),
            "rating": self.rating,
            "review_datetime": self.review_datetime.isoformat(),
            "review_duration": self.review_duration,
        }

        return return_dict

    @staticmethod
    def from_dict(source_dict: dict[str, Any]) -> "ReviewLog":
        card = Card.from_dict(source_dict["card"])
        rating = int(source_dict["rating"])
        review_datetime = datetime.fromisoformat(source_dict["review_datetime"])
        review_duration = source_dict["review_duration"]

        return ReviewLog(
            card=card,
            rating=rating,
            review_datetime=review_datetime,
            review_duration=review_duration,
        )


class Scheduler:
    @staticmethod
    def review_card(
        card: Card,
        rating: int,
        review_datetime: datetime | None = None,
        review_duration: int | None = None,
    ) -> tuple[Card, ReviewLog]:

        card = deepcopy(card)

        if review_datetime is None:
            review_datetime = datetime.now(timezone.utc)

        card_is_due = review_datetime >= card.due

        if not card_is_due:
            time_until_due = (card.due - review_datetime).total_seconds()
            if time_until_due > 60:
                raise RuntimeError(f"Card is not due for review until {card.due}.")

        review_log = ReviewLog(
            card=card,
            rating=rating,
            review_datetime=review_datetime,
            review_duration=review_duration,
        )

        if card.needs_extra_review:
            if rating >= 4:
                card.needs_extra_review = False
                card.due += timedelta(days=card.I)

        else:
            if rating >= 3:
                card.EF = card.EF + (0.1 - (5 - rating) * (0.08 + (5 - rating) * 0.02))
                card.EF = max(1.3, card.EF)

                if card.n == 0:
                    card.I = 1

                elif card.n == 1:
                    card.I = 6

                else:
                    card.I = ceil(card.I * card.EF)

                card.n += 1

                if rating >= 4:
                    card.due += timedelta(days=card.I)

                else:
                    card.needs_extra_review = True
                    card.due = review_datetime

            else:
                card.n = 0
                card.I = 0
                card.due = review_datetime

        return card, review_log


__all__ = ["Scheduler", "Card", "ReviewLog"]