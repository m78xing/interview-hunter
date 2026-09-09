"""
LearningRouter 单元测试
"""
import pytest
from unittest.mock import MagicMock
from src.agents.learning_router import LearningRouter


class TestLearningRouter:
    def setup_method(self):
        self.mock_llM = MagicMock()
        self.mock_store = MagicMock()
        self.router = LearningRouter(llm_client=self.mock_llM, preference_store=self.mock_store)

    def test_route_returns_mode(self):
        self.mock_llM.chat_json.return_value = {
            "mode": "anxiety_relief",
            "confidence": 0.9,
            "reason": "test",
        }
        result = self.router.route("最近好焦虑")
        assert result["mode"] == "anxiety_relief"

    def test_route_defaults_to_anxiety_relief(self):
        self.mock_llM.chat_json.return_value = {}
        result = self.router.route("test")
        assert result["mode"] == "anxiety_relief"

    def test_route_handles_modify_keywords_replace(self):
        self.mock_llM.chat_json.return_value = {
            "mode": "modify_keywords",
            "keywords": ["redis"],
            "action": "replace",
            "confidence": 0.9,
        }
        self.router.route("改成搜索redis")
        self.mock_store.save_keywords.assert_called_once_with("default", ["redis"])

    def test_route_handles_modify_keywords_add(self):
        self.mock_llM.chat_json.return_value = {
            "mode": "modify_keywords",
            "keywords": ["百度"],
            "action": "add",
            "confidence": 0.9,
        }
        self.router.route("加上百度")
        self.mock_store.add_keyword.assert_called_once_with("default", "百度")

    def test_route_handles_modify_keywords_delete(self):
        self.mock_llM.chat_json.return_value = {
            "mode": "modify_keywords",
            "keywords": ["redis"],
            "action": "delete",
            "confidence": 0.9,
        }
        self.router.route("删除redis")
        self.mock_store.remove_keyword.assert_called_once_with("default", "redis")

    def test_route_handles_none_action(self):
        self.mock_llM.chat_json.return_value = {
            "mode": "modify_keywords",
            "keywords": [],
            "action": "none",
            "confidence": 0.9,
        }
        self.router.route("test")
        self.mock_store.save_keywords.assert_not_called()
        self.mock_store.add_keyword.assert_not_called()
        self.mock_store.remove_keyword.assert_not_called()
