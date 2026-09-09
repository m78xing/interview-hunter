"""
InterviewSimAgent 单元测试
"""
import pytest
from unittest.mock import MagicMock
from src.agents.interview_agent import InterviewSimAgent


class TestInterviewSimAgent:
    def setup_method(self):
        self.mock_llM = MagicMock()
        self.mock_rag = MagicMock()
        self.agent = InterviewSimAgent(llm_client=self.mock_llM, rag_manager=self.mock_rag)

    def test_set_resume_parses_and_starts_interview(self):
        self.mock_llM.chat_json.return_value = {
            "name": "张三",
            "target_position": "后端",
            "skills": ["Python", "Redis"],
            "projects": ["电商系统"],
            "experience_years": 3,
        }
        self.mock_llM.chat.return_value = "介绍一下你的电商系统？"

        result = self.agent.set_resume("简历内容...")
        assert "介绍一下你的电商系统？" in result
        assert self.agent.stage == "interviewing"
        assert self.agent.question_count == 1

    def test_handle_answer_generates_followup(self):
        self.agent.stage = "interviewing"
        self.agent.question_count = 1
        self.agent.conversation_history = [
            {"role": "interviewer", "content": "Q1"},
        ]
        self.mock_llM.chat.return_value = "追问：能详细说说吗？"

        result = self.agent.handle_answer("My answer")
        assert "追问" in result
        assert self.agent.question_count == 2

    def test_handle_answer_triggers_evaluation_at_max(self):
        self.agent.stage = "interviewing"
        self.agent.question_count = 10
        self.agent.max_questions = 10
        self.agent.conversation_history = []
        self.mock_llM.chat.return_value = "面试评估报告"

        result = self.agent.handle_answer("Final answer")
        assert "面试评估报告" in result
        assert self.agent.stage == "evaluating"

    def test_evaluate_returns_report(self):
        self.agent.stage = "interviewing"
        self.agent.conversation_history = [
            {"role": "interviewer", "content": "Q1"},
            {"role": "candidate", "content": "A1"},
        ]
        self.mock_llM.chat.return_value = "技术深度: 7/10"

        result = self.agent.evaluate()
        assert "技术深度" in result

    def test_start_without_resume(self):
        self.mock_llM.chat.return_value = "What is your experience with distributed systems?"

        result = self.agent.start_without_resume()
        assert self.agent.stage == "interviewing"
        assert self.agent.question_count == 1
        assert result == "What is your experience with distributed systems?"

    def test_reset_clears_state(self):
        self.agent.resume_context = {"name": "张三"}
        self.agent.conversation_history = [{"role": "interviewer", "content": "Q"}]
        self.agent.stage = "evaluating"
        self.agent.question_count = 5

        self.agent.reset()
        assert self.agent.resume_context == {}
        assert self.agent.conversation_history == []
        assert self.agent.stage == "init"
        assert self.agent.question_count == 0

    def test_format_history(self):
        self.agent.conversation_history = [
            {"role": "interviewer", "content": "Q1"},
            {"role": "candidate", "content": "A1"},
        ]
        result = self.agent._format_history()
        assert "面试官: Q1" in result
        assert "候选人: A1" in result
