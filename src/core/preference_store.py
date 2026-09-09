"""
User Preference Store - 轻量级用户偏好存储（长期记忆）
"""
import json
import logging
from pathlib import Path
from typing import List
from datetime import datetime

logger = logging.getLogger(__name__)


class UserPreferenceStore:
    def __init__(self, storage_path: str = "./memory/preferences"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def save_keywords(self, user_id: str, keywords: List[str]):
        file = self.storage_path / f"{user_id}_keywords.json"
        with open(file, "w", encoding="utf-8") as f:
            json.dump({
                "user_id": user_id,
                "keywords": keywords,
                "updated_at": datetime.now().isoformat(),
            }, f, ensure_ascii=False, indent=2)
        logger.info(f"Keywords saved for {user_id}: {keywords}")

    def get_keywords(self, user_id: str) -> List[str]:
        file = self.storage_path / f"{user_id}_keywords.json"
        if file.exists():
            with open(file, encoding="utf-8") as f:
                return json.load(f).get("keywords", [])
        return []

    def add_keyword(self, user_id: str, keyword: str):
        keywords = self.get_keywords(user_id)
        if keyword not in keywords:
            keywords.append(keyword)
            self.save_keywords(user_id, keywords)

    def remove_keyword(self, user_id: str, keyword: str):
        keywords = self.get_keywords(user_id)
        if keyword in keywords:
            keywords.remove(keyword)
            self.save_keywords(user_id, keywords)
