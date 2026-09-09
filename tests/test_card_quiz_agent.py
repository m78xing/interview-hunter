"""
CardQuizAgent 单元测试
"""
import pytest
from unittest.mock import MagicMock
from src.agents.card_quiz_agent import CardQuizAgent


class TestCardQuizAgent:
    def setup_method(self):
        self.mock_llM = MagicMock()
        self.mock_rag = MagicMock()
        self.mock_sqlite = MagicMock()
        self.agent = CardQuizAgent(
            llm_client=self.mock_llM,
            rag_manager=self.mock_rag,
            sqlite_client=self.mock_sqlite,
        )

    def test_start_quiz_with_topic_returns_question(self):
        mock_result = MagicMock()
        mock_result.card_id = "c1"
        self.mock_rag.search.return_value = [mock_result]
        mock_card = MagicMock()
        mock_card.question = "What is quicksort?"
        self.mock_sqlite.get_card.return_value = mock_card

        result = self.agent.start_quiz(topic="sorting")
        assert "What is quicksort?" in result
        assert self.agent.waiting_answer is True

    def test_start_quiz_without_topic_uses_due_cards(self):
        self.mock_sqlite.get_due_cards.return_value = ["c1"]
        mock_card = MagicMock()
        mock_card.question = "What is TCP?"
        self.mock_sqlite.get_card.return_value = mock_card

        result = self.agent.start_quiz()
        assert "What is TCP?" in result

    def test_start_quiz_no_cards_returns_message(self):
        self.mock_rag.search.return_value = []
        result = self.agent.start_quiz(topic="nonexistent")
        assert "暂无可复习的卡片" in result

    def test_check_answer_returns_evaluation(self):
        mock_card = MagicMock()
        mock_card.question = "Q"
        mock_card.answer = "A"
        self.agent.current_card = mock_card
        self.agent.waiting_answer = True
        self.mock_llM.chat.return_value = "Good answer, 80/100"

        result = self.agent.check_answer("User says O(nlogn)")
        assert "A" in result
        assert "Good answer" in result
        assert self.agent.waiting_answer is False

    def test_check_answer_without_current_card_starts_new_quiz(self):
        self.agent.current_card = None
        self.mock_sqlite.get_due_cards.return_value = ["c1"]
        mock_card = MagicMock()
        mock_card.question = "New Q"
        self.mock_sqlite.get_card.return_value = mock_card

        result = self.agent.check_answer("test")
        assert "New Q" in result

    def test_chat_answers_question_when_not_waiting(self):
        self.agent.waiting_answer = False
        mock_result = MagicMock()
        mock_result.card_id = "c1"
        self.mock_rag.search.return_value = [mock_result]
        mock_card = MagicMock()
        mock_card.question = "Q"
        mock_card.answer = "A"
        self.mock_sqlite.get_card.return_value = mock_card
        self.mock_llM.chat.return_value = "LLM answer"

        result = self.agent.chat("Tell me about sorting")
        assert result["response"] == "LLM answer"
        assert len(result["sources"]) > 0

    def test_chat_triggers_check_answer_when_waiting(self):
        mock_card = MagicMock()
        mock_card.question = "Q"
        mock_card.answer = "A"
        self.agent.current_card = mock_card
        self.agent.waiting_answer = True
        self.mock_llM.chat.return_value = "Evaluation"

        result = self.agent.chat("My answer")
        assert "Evaluation" in result["response"]
