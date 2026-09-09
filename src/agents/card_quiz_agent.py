"""
卡片问答 Agent
"""
import logging
from typing import Optional, Callable

from src.core.llm_client import LLMClient
from src.core.rag_manager import RagManager
from src.storage.sqlite_client import SQLiteClient, Card

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个面经学习助手。
- 根据搜索结果回答用户问题
- 如果搜索到相关卡片，优先参考卡片内容
- 如果搜索结果为空，基于你的知识回答
- 回答简洁明了，重点突出"""


class CardQuizAgent:
    def __init__(self, llm_client: LLMClient, rag_manager: RagManager, sqlite_client: SQLiteClient):
        self.llm = llm_client
        self.rag = rag_manager
        self.sqlite = sqlite_client
        self.current_card: Optional[Card] = None
        self.waiting_answer = False

    def start_quiz(self, topic: Optional[str] = None) -> str:
        if topic:
            results = self.rag.search(topic, limit=1)
            if results:
                card = self.sqlite.get_card(results[0].card_id)
            else:
                card = None
        else:
            due_ids = self.sqlite.get_due_cards(limit=1)
            card = self.sqlite.get_card(due_ids[0]) if due_ids else None

        if not card:
            return "暂无可复习的卡片"

        self.current_card = card
        self.waiting_answer = True
        return f"📚 问题：{card.question}"

    def check_answer(self, user_answer: str) -> str:
        if not self.current_card or not self.waiting_answer:
            return self.start_quiz()

        self.waiting_answer = False
        card = self.current_card

        evaluation = self.llm.chat(
            messages=[{"role": "user", "content": f"用户回答：{user_answer}\n\n标准答案：{card.answer}\n\n请评价用户回答，指出正确/错误/遗漏之处，并给出评分（0-100）。"}],
            temperature=0.3,
        )

        self.current_card = None
        return f"✅ 标准答案：{card.answer}\n\n📝 评价：{evaluation}"

    def chat(self, user_message: str, history: Optional[list] = None) -> dict:
        if self.waiting_answer:
            return {"response": self.check_answer(user_message), "sources": []}

        results = self.rag.search(user_message, limit=5)

        search_context = ""
        sources = []
        if results:
            search_context = "\n搜索到的面经卡片：\n"
            for i, r in enumerate(results[:3], 1):
                card = self.sqlite.get_card(r.card_id)
                if card:
                    search_context += f"{i}. 问题：{card.question}\n   答案：{card.answer[:300]}\n\n"
                    sources.append({
                        "card_id": card.id,
                        "question": card.question,
                        "company": card.company,
                        "position": card.position,
                        "similarity": r.score if hasattr(r, 'score') else 0.0,
                    })

        messages = [{"role": "user", "content": user_message}]

        system = SYSTEM_PROMPT
        if search_context:
            system += f"\n\n{search_context}"

        response = self.llm.chat(
            messages=messages,
            system_prompt=system,
            temperature=0.7,
        )
        return {"response": response, "sources": sources}

    def chat_stream(
        self,
        user_message: str,
        history: Optional[list] = None,
        on_thinking: Optional[Callable[[str], None]] = None,
        on_content: Optional[Callable[[str], None]] = None,
    ) -> dict:
        if self.waiting_answer:
            return {"response": self.check_answer(user_message), "sources": []}

        results = self.rag.search(user_message, limit=5)

        search_context = ""
        sources = []
        if results:
            search_context = "\n搜索到的面经卡片：\n"
            for i, r in enumerate(results[:3], 1):
                card = self.sqlite.get_card(r.card_id)
                if card:
                    search_context += f"{i}. 问题：{card.question}\n   答案：{card.answer[:300]}\n\n"
                    sources.append({
                        "card_id": card.id,
                        "question": card.question,
                        "company": card.company,
                        "position": card.position,
                        "similarity": r.score if hasattr(r, 'score') else 0.0,
                    })

        messages = [{"role": "user", "content": user_message}]

        system = SYSTEM_PROMPT
        if search_context:
            system += f"\n\n{search_context}"

        response = self.llm.stream_chat(
            messages=messages,
            system_prompt=system,
            temperature=0.7,
            on_thinking=on_thinking,
            on_content=on_content,
        )
        return {"response": response, "sources": sources}
