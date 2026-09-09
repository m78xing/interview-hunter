"""
UserPreferenceStore 单元测试
"""
import json
import pytest
import tempfile
from pathlib import Path
from src.core.preference_store import UserPreferenceStore


class TestUserPreferenceStore:
    def setup_method(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.store = UserPreferenceStore(storage_path=self.tmp_dir)

    def teardown_method(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_save_and_get_keywords(self):
        self.store.save_keywords("user1", ["redis", "阿里"])
        result = self.store.get_keywords("user1")
        assert result == ["redis", "阿里"]

    def test_get_keywords_returns_empty_for_new_user(self):
        result = self.store.get_keywords("nonexistent")
        assert result == []

    def test_add_keyword(self):
        self.store.save_keywords("user1", ["redis"])
        self.store.add_keyword("user1", "阿里")
        result = self.store.get_keywords("user1")
        assert "阿里" in result
        assert "redis" in result

    def test_add_keyword_no_duplicate(self):
        self.store.save_keywords("user1", ["redis"])
        self.store.add_keyword("user1", "redis")
        result = self.store.get_keywords("user1")
        assert result.count("redis") == 1

    def test_remove_keyword(self):
        self.store.save_keywords("user1", ["redis", "阿里"])
        self.store.remove_keyword("user1", "redis")
        result = self.store.get_keywords("user1")
        assert "redis" not in result
        assert "阿里" in result

    def test_remove_nonexistent_keyword(self):
        self.store.save_keywords("user1", ["redis"])
        self.store.remove_keyword("user1", "nonexistent")
        result = self.store.get_keywords("user1")
        assert result == ["redis"]

    def test_save_keywords_creates_file(self):
        self.store.save_keywords("user1", ["test"])
        file_path = Path(self.tmp_dir) / "user1_keywords.json"
        assert file_path.exists()

    def test_save_keywords_writes_valid_json(self):
        self.store.save_keywords("user1", ["test"])
        file_path = Path(self.tmp_dir) / "user1_keywords.json"
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        assert "user_id" in data
        assert "keywords" in data
        assert "updated_at" in data
