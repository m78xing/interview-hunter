"""
DailyMissionManager 单元测试
"""
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch
from datetime import date
from src.core.daily_mission import DailyMission, DailyMissionManager


class TestDailyMission:
    def test_creation(self):
        mission = DailyMission(
            user_id="user1",
            date="2026-04-03",
            card_ids=["c1", "c2"],
        )
        assert mission.user_id == "user1"
        assert mission.date == "2026-04-03"
        assert mission.card_ids == ["c1", "c2"]
        assert mission.is_locked is True
        assert mission.created_at

    def test_to_dict(self):
        mission = DailyMission(user_id="u1", date="2026-04-03", card_ids=["c1"])
        data = mission.to_dict()
        assert data["user_id"] == "u1"
        assert data["card_ids"] == ["c1"]

    def test_from_dict(self):
        data = {"user_id": "u1", "date": "2026-04-03", "card_ids": ["c1"], "is_locked": True, "created_at": "now"}
        mission = DailyMission.from_dict(data)
        assert mission.user_id == "u1"


class TestDailyMissionManager:
    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.mock_sqlite = MagicMock()
        self.mock_sqlite.get_card_stats.return_value = {}
        self.manager = DailyMissionManager(
            sqlite_client=self.mock_sqlite,
            storage_path=self.tmp_dir,
        )

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _make_card(self, card_id, company="字节", position="后端", difficulty="medium", tags=None):
        card = MagicMock()
        card.id = card_id
        card.company = company
        card.position = position
        card.difficulty = difficulty
        card.tags = tags or ["算法"]
        return card

    def test_select_daily_cards_returns_cards(self):
        cards = [self._make_card(f"c{i}") for i in range(15)]
        self.mock_sqlite.get_all_cards.return_value = cards
        self.mock_sqlite.get_card.side_effect = lambda cid: next((c for c in cards if c.id == cid), None)

        result = self.manager.select_daily_cards(limit=10)
        assert len(result) == 10

    def test_select_daily_cards_empty_database(self):
        self.mock_sqlite.get_all_cards.return_value = []
        result = self.manager.select_daily_cards()
        assert result == []

    def test_select_daily_cards_uses_priority_ordering(self):
        cards = [self._make_card(f"c{i}") for i in range(5)]
        self.mock_sqlite.get_all_cards.return_value = cards
        self.mock_sqlite.get_card_stats.return_value = {
            "interval_days": 10,
            "ease_factor": 2.0,
            "correct_count": 1,
            "total_reviews": 5,
        }
        self.mock_sqlite.get_card.side_effect = lambda cid: next((c for c in cards if c.id == cid), None)

        result = self.manager.select_daily_cards(limit=5)
        assert len(result) == 5

    def test_select_daily_cards_locks_after_selection(self):
        cards = [self._make_card(f"c{i}") for i in range(10)]
        self.mock_sqlite.get_all_cards.return_value = cards
        self.mock_sqlite.get_card.side_effect = lambda cid: next((c for c in cards if c.id == cid), None)

        self.manager.select_daily_cards(limit=10)
        assert self.manager.current_mission is not None
        assert self.manager.current_mission.is_locked is True

    def test_reset_daily_clears_and_reselects(self):
        cards = [self._make_card(f"c{i}") for i in range(10)]
        self.mock_sqlite.get_all_cards.return_value = cards
        self.mock_sqlite.get_card.side_effect = lambda cid: next((c for c in cards if c.id == cid), None)

        self.manager.select_daily_cards(limit=10)
        old_ids = self.manager.current_mission.card_ids.copy()

        self.manager.reset_daily()
        assert self.manager.current_mission is not None
        assert self.manager.current_mission.date == date.today().isoformat()

    def test_mission_file_persisted(self):
        cards = [self._make_card(f"c{i}") for i in range(5)]
        self.mock_sqlite.get_all_cards.return_value = cards
        self.mock_sqlite.get_card.side_effect = lambda cid: next((c for c in cards if c.id == cid), None)

        self.manager.select_daily_cards(limit=5)
        today = date.today().isoformat()
        file_path = Path(self.tmp_dir) / f"default_{today}.json"
        assert file_path.exists()

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        assert len(data["card_ids"]) == 5
