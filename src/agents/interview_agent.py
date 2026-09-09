"""
面试模拟 Agent
"""
import logging
from typing import Optional, Callable

from src.core.llm_client import LLMClient
from src.core.rag_manager import RagManager

logger = logging.getLogger(__name__)

RESUME_PARSE_PROMPT = """你是一个简历解析器。从以下简历中提取关键信息：

{resume_text}

返回JSON：
{{
    "name": "姓名",
    "target_position": "目标岗位",
    "skills": ["技能1", "技能2"],
    "projects": ["项目1", "项目2"],
    "experience_years": 工作年限
}}

只返回 JSON。"""

INTERVIEW_SYSTEM_PROMPT = """你是一个资深技术面试官。
- 根据用户简历提出面试问题
- 深入追问技术细节
- 识别回答中的漏洞和错误
- 保持专业、友善的面试风格
- 每次只问一个问题，等待用户回答"""

EVALUATE_PROMPT = """你是一个技术面试官。请根据以下面试对话给出评估：

{conversation}

请从以下维度评估：
1. 技术深度（0-10分）
2. 表达能力（0-10分）
3. 项目经验（0-10分）
4. 发现的错误和漏洞
5. 改进建议

返回结构化的评估报告。"""


class InterviewSimAgent:
    def __init__(self, llm_client: LLMClient, rag_manager: RagManager):
        self.llm = llm_client
        self.rag = rag_manager
        self.resume_context: dict = {}
        self.conversation_history: list = []
        self.stage: str = "init"
        self.question_count: int = 0
        self.max_questions: int = 10

    def set_resume(self, resume_text: str) -> str:
        parsed = self.llm.chat_json(
            user_message=RESUME_PARSE_PROMPT.format(resume_text=resume_text),
            temperature=0.3,
        )
        self.resume_context = parsed
        self.stage = "interviewing"
        self.question_count = 0

        first_question = self.llm.chat(
            messages=[{"role": "user", "content": "基于以下简历信息，提出第一个面试问题（只问一个问题）：\n" + str(parsed)}],
            system_prompt=INTERVIEW_SYSTEM_PROMPT,
            temperature=0.7,
        )
        self.conversation_history.append({"role": "interviewer", "content": first_question})
        self.question_count += 1
        return first_question

    def set_resume_stream(
        self,
        resume_text: str,
        on_thinking: Optional[Callable[[str], None]] = None,
        on_content: Optional[Callable[[str], None]] = None,
    ) -> str:
        parsed = self.llm.chat_json(
            user_message=RESUME_PARSE_PROMPT.format(resume_text=resume_text),
            temperature=0.3,
        )
        self.resume_context = parsed
        self.stage = "interviewing"
        self.question_count = 0

        first_question = self.llm.stream_chat(
            messages=[{"role": "user", "content": "基于以下简历信息，提出第一个面试问题（只问一个问题）：\n" + str(parsed)}],
            system_prompt=INTERVIEW_SYSTEM_PROMPT,
            temperature=0.7,
            on_thinking=on_thinking,
            on_content=on_content,
        )
        self.conversation_history.append({"role": "interviewer", "content": first_question})
        self.question_count += 1
        return first_question

    def handle_answer(self, user_answer: str) -> str:
        self.conversation_history.append({"role": "candidate", "content": user_answer})

        if self.question_count >= self.max_questions:
            return self.evaluate()

        followup = self.llm.chat(
            messages=[
                {"role": "user", "content": f"候选人回答：{user_answer}\n\n对话历史：{self._format_history()}\n\n请根据回答提出下一个问题或深入追问（只问一个问题）："}
            ],
            system_prompt=INTERVIEW_SYSTEM_PROMPT,
            temperature=0.7,
        )
        self.conversation_history.append({"role": "interviewer", "content": followup})
        self.question_count += 1
        return followup

    def handle_answer_stream(
        self,
        user_answer: str,
        on_thinking: Optional[Callable[[str], None]] = None,
        on_content: Optional[Callable[[str], None]] = None,
    ) -> str:
        self.conversation_history.append({"role": "candidate", "content": user_answer})

        if self.question_count >= self.max_questions:
            return self.evaluate_stream(on_thinking=on_thinking, on_content=on_content)

        followup = self.llm.stream_chat(
            messages=[
                {"role": "user", "content": f"候选人回答：{user_answer}\n\n对话历史：{self._format_history()}\n\n请根据回答提出下一个问题或深入追问（只问一个问题）："}
            ],
            system_prompt=INTERVIEW_SYSTEM_PROMPT,
            temperature=0.7,
            on_thinking=on_thinking,
            on_content=on_content,
        )
        self.conversation_history.append({"role": "interviewer", "content": followup})
        self.question_count += 1
        return followup

    def evaluate(self) -> str:
        self.stage = "evaluating"
        evaluation = self.llm.chat(
            messages=[{"role": "user", "content": EVALUATE_PROMPT.format(conversation=self._format_history())}],
            temperature=0.3,
        )
        return evaluation

    def evaluate_stream(
        self,
        on_thinking: Optional[Callable[[str], None]] = None,
        on_content: Optional[Callable[[str], None]] = None,
    ) -> str:
        self.stage = "evaluating"
        evaluation = self.llm.stream_chat(
            messages=[{"role": "user", "content": EVALUATE_PROMPT.format(conversation=self._format_history())}],
            temperature=0.3,
            on_thinking=on_thinking,
            on_content=on_content,
        )
        return evaluation

    def start_without_resume(self) -> str:
        self.stage = "interviewing"
        self.question_count = 0

        first_question = self.llm.chat(
            messages=[{"role": "user", "content": "作为技术面试官，请提出第一个通用技术问题（只问一个问题）："}],
            system_prompt=INTERVIEW_SYSTEM_PROMPT,
            temperature=0.7,
        )
        self.conversation_history.append({"role": "interviewer", "content": first_question})
        self.question_count += 1
        return first_question

    def start_without_resume_stream(
        self,
        on_thinking: Optional[Callable[[str], None]] = None,
        on_content: Optional[Callable[[str], None]] = None,
    ) -> str:
        self.stage = "interviewing"
        self.question_count = 0

        first_question = self.llm.stream_chat(
            messages=[{"role": "user", "content": "作为技术面试官，请提出第一个通用技术问题（只问一个问题）："}],
            system_prompt=INTERVIEW_SYSTEM_PROMPT,
            temperature=0.7,
            on_thinking=on_thinking,
            on_content=on_content,
        )
        self.conversation_history.append({"role": "interviewer", "content": first_question})
        self.question_count += 1
        return first_question

    def _format_history(self) -> str:
        parts = []
        for msg in self.conversation_history:
            role = "面试官" if msg["role"] == "interviewer" else "候选人"
            parts.append(f"{role}: {msg['content']}")
        return "\n\n".join(parts)

    def reset(self):
        self.resume_context = {}
        self.conversation_history = []
        self.stage = "init"
        self.question_count = 0
