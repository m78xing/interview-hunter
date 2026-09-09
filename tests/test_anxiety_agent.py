"""
AnxietyReliefAgent 单元测试
"""
import pytest
from unittest.mock import MagicMock
from src.agents.anxiety_agent import AnxietyReliefAgent


class TestAnxietyReliefAgent:
    def setup_method(self):
        self.mock_llM = MagicMock()
        self.agent = AnxietyReliefAgent(llm_client=self.mock_llM)

    def test_chat_returns_response(self):
        self.mock_llM.chat.return_value = "我理解你的感受"
        result = self.agent.chat("最近好焦虑")
        assert result == "我理解你的感受"

    def test_chat_passes_user_message(self):
        self.mock_llM.chat.return_value = "response"
        self.agent.chat("test message")
        call_args = self.mock_llM.chat.call_args
        messages = call_args.kwargs["messages"]
        assert messages[-1]["content"] == "test message"

    def test_chat_passes_history(self):
        self.mock_llM.chat.return_value = "response"
        history = [{"role": "user", "content": "Hi"}]
        self.agent.chat("Hello", history=history)
        call_args = self.mock_llM.chat.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["content"] == "Hi"

    def test_chat_uses_high_temperature(self):
        self.mock_llM.chat.return_value = "response"
        self.agent.chat("test")
        call_args = self.mock_llM.chat.call_args
        assert call_args.kwargs["temperature"] == 0.8
