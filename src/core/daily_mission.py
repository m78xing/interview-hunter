"""
Daily Mission Manager - 基于 SM-2 算法选取每日面经
"""
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime, date, timezone
from pathlib import Path
from typing import List, Optional

from src.storage.sqlite_client import SQLiteClient, Card as SQLiteCard

logger = logging.getLogger(__name__)


@dataclass
class DailyMission:
    user_id: str
    date: str
    card_ids: List[str]
    is_locked: bool = True
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        return cls(**data)


class DailyMissionManager:
    def __init__(self, sqlite_client: SQLiteClient, storage_path: str = "./memory/daily_missions"):
        self.sqlite = sqlite_client
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.current_mission: Optional[DailyMission] = None
        self._load_current_mission("default")

    def _load_current_mission(self, user_id: str):
        today = date.today().isoformat()
        file = self.storage_path / f"{user_id}_{today}.json"
        if file.exists():
            with open(file, encoding="utf-8") as f:
                data = json.load(f)
                self.current_mission = DailyMission.from_dict(data)
                logger.info(f"Loaded daily mission for {user_id}: {len(data['card_ids'])} cards")

    def select_daily_cards(self, user_id: str = "default", limit: int = 10) -> List[SQLiteCard]:
        today = date.today().isoformat()

        if self.current_mission and self.current_mission.date == today and self.current_mission.is_locked:
            card_ids = self.current_mission.card_ids
            return self._load_cards(card_ids)

        all_cards = self.sqlite.get_all_cards()
        if not all_cards:
            return []

        now = datetime.now(timezone.utc)
        due_cards = []
        new_cards = []

        for card in all_cards:
            stats = self.sqlite.get_card_stats(card.id)
            
            if not stats or stats.get('total_reviews', 0) == 0:
                new_cards.append(card)
                continue
            
            due_str = stats.get('due')
            if due_str:
                try:
                    due = datetime.fromisoformat(due_str.replace('Z', '+00:00'))
                except:
                    due_cards.append(card)
                    continue
                if due <= now:
                    due_cards.append(card)
            else:
                due_cards.append(card)

        selected = []

        due_cards.sort(key=lambda c: (self.sqlite.get_card_stats(c.id) or {}).get('due', ''))
        for card in due_cards:
            if len(selected) >= limit:
                break
            selected.append(card)

        if len(selected) < limit:
            for card in new_cards:
                if len(selected) >= limit:
                    break
                if card not in selected:
                    selected.append(card)

        card_ids = [c.id for c in selected]

        self.current_mission = DailyMission(
            user_id=user_id,
            date=today,
            card_ids=card_ids,
            is_locked=True,
        )
        self._save_mission(self.current_mission)
        logger.info(f"Daily mission created: {len(card_ids)} cards (due={len(due_cards)}, new={len(new_cards)})")

        return selected

    def _load_cards(self, card_ids: List[str]) -> List[SQLiteCard]:
        cards = []
        for cid in card_ids:
            card = self.sqlite.get_card(cid)
            if card:
                cards.append(card)
        return cards

    def _save_mission(self, mission: DailyMission):
        file = self.storage_path / f"{mission.user_id}_{mission.date}.json"
        with open(file, "w", encoding="utf-8") as f:
            json.dump(mission.to_dict(), f, ensure_ascii=False, indent=2)

    def reset_daily(self, user_id: str = "default"):
        self.current_mission = None
        today = date.today().isoformat()
        file = self.storage_path / f"{user_id}_{today}.json"
        if file.exists():
            file.unlink()
        logger.info(f"Daily mission reset for {user_id}")
        return self.select_daily_cards(user_id)

    def record_familiarity(self, card_id: str, familiarity: int):
        from sm_2 import Scheduler, Card as SM2Card
        
        FAMILIARITY_TO_QUALITY = {
            0: 0,
            1: 1,
            2: 3,
            3: 4,
            4: 5,
        }
        quality = FAMILIARITY_TO_QUALITY.get(familiarity, 3)
        review_datetime = datetime.now(timezone.utc)

        sm2_card = self.sqlite.get_sm2_card(card_id)
        
        if sm2_card:
            updated_card, review_log = Scheduler.review_card(sm2_card, quality, review_datetime)
            
            self.sqlite.add_review_log(card_id, quality)
            self.sqlite.update_card_from_sm2(card_id, updated_card)
            
            logger.info(f"SM-2 review: card={card_id}, quality={quality}, n={updated_card.n}, I={updated_card.I}, due={updated_card.due}")
        else:
            self.sqlite.add_review_log(card_id, quality)
            logger.warning(f"Card not found for SM-2: {card_id}")

        self.reset_daily()