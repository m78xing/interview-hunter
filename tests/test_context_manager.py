"""
ContextManager 单元测试
"""
import pytest
from unittest.mock import MagicMock
from src.core.context_manager import ContextManager


class TestContextManager:
    def setup_method(self):
        self.mock_store = MagicMock()
        self.mock_llM = MagicMock()
        self.manager = ContextManager(
            context_store=self.mock_store,
            llm_client=self.mock_llM,
            max_turns=3,
            summary_threshold=5,
        )

    def test_get_context_returns_empty_when_no_history(self):
        self.mock_store.load_latest_context.return_value = None
        result = self.manager.get_context("session_1")
        assert result == ""

    def test_get_context_returns_recent_turns_under_threshold(self):
        history = {
            "chat_history": [
                {"role": "user", "content": "Hi"},
                {"role": "assistant", "content": "Hello"},
            ],
            "version": 1,
        }
        self.mock_store.load_latest_context.return_value = history
        result = self.manager.get_context("session_1")
        assert "用户: Hi" in result
        assert "助手: Hello" in result

    def test_get_context_truncates_to_max_turns(self):
        turns = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"msg{i}"} for i in range(10)]
        history = {"chat_history": turns, "version": 1}
        self.mock_store.load_latest_context.return_value = history
        result = self.manager.get_context("session_1")
        assert "msg8" in result
        assert "msg9" in result
        assert "msg0" not in result

    def test_get_context_triggers_summarization(self):
        turns = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"msg{i}"} for i in range(12)]
        history = {"chat_history": turns, "version": 1}
        self.mock_store.load_latest_context.return_value = history
        self.mock_llM.chat.return_value = "Summary of old messages"

        result = self.manager.get_context("session_1")
        assert "[历史摘要]" in result
        assert "Summary of old messages" in result
        assert "msg10" in result
        assert "msg0" not in result

    def test_save_turn_adds_message(self):
        self.mock_store.load_latest_context.return_value = {"chat_history": [], "version": 0}
        self.manager.save_turn("session_1", "user", "Hello")
        self.mock_store.save_context.assert_called_once()
        call_args = self.mock_store.save_context.call_args
        assert call_args[0][1]["chat_history"][-1]["content"] == "Hello"

    def test_save_turn_appends_to_existing_history(self):
        self.mock_store.load_latest_context.return_value = {
            "chat_history": [{"role": "user", "content": "First"}],
            "version": 1,
        }
        self.manager.save_turn("session_1", "assistant", "Response")
        call_args = self.mock_store.save_context.call_args
        history = call_args[0][1]["chat_history"]
        assert len(history) == 2
        assert history[1]["content"] == "Response"
