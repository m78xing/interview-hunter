"""
Learning Router - 对话学习入口，自动判断用户意图并路由
"""
import logging
from typing import Optional, Callable

from src.core.llm_client import LLMClient
from src.core.preference_store import UserPreferenceStore

logger = logging.getLogger(__name__)

ROUTE_PROMPT = """你是一个对话学习路由器。

用户消息：{user_message}

判断用户想要什么模式（返回JSON）：
{{
    "mode": "anxiety_relief" | "card_quiz" | "interview_sim" | "modify_keywords",
    "keywords": ["关键字1", "关键字2"],
    "action": "add" | "delete" | "replace" | "none",
    "confidence": 0.0-1.0,
    "reason": "理由"
}}

模式说明：
- anxiety_relief: 用户在倾诉消极情绪、压力、焦虑，或者只是闲聊/打招呼
- card_quiz: 用户想学习/复习面经卡片，问答形式
- interview_sim: 用户想模拟面试，会提供简历或要求开始面试
- modify_keywords: 用户想修改爬虫关键字（"改成搜索xxx"、"加上xxx"、"删除xxx"等）

只返回 JSON。"""


class LearningRouter:
    def __init__(self, llm_client: LLMClient, preference_store: UserPreferenceStore):
        self.llm = llm_client
        self.preference_store = preference_store

    def route(self, user_message: str, current_mode: Optional[str] = None) -> dict:
        result = self.llm.chat_json(
            user_message=user_message,
            system_prompt=ROUTE_PROMPT,
            temperature=0.3,
        )

        mode = result.get("mode", "anxiety_relief")
        result["mode"] = mode
        logger.info(f"Route result: mode={mode}, confidence={result.get('confidence')}")

        if mode == "modify_keywords":
            self._handle_keywords(result)

        return result

    def route_stream(
        self,
        user_message: str,
        current_mode: Optional[str] = None,
        on_thinking: Optional[Callable[[str], None]] = None,
    ) -> dict:
        result = self.llm.chat_json(
            user_message=user_message,
            system_prompt=ROUTE_PROMPT,
            temperature=0.3,
        )

        mode = result.get("mode", "anxiety_relief")
        result["mode"] = mode
        logger.info(f"Route result: mode={mode}, confidence={result.get('confidence')}")

        if mode == "modify_keywords":
            self._handle_keywords(result)

        return result

    def _handle_keywords(self, result: dict):
        keywords = result.get("keywords", [])
        action = result.get("action", "none")

        if not keywords or action == "none":
            return

        if action == "replace":
            self.preference_store.save_keywords("default", keywords)
        elif action == "add":
            for kw in keywords:
                self.preference_store.add_keyword("default", kw)
        elif action == "delete":
            for kw in keywords:
                self.preference_store.remove_keyword("default", kw)

        logger.info(f"Keywords updated: action={action}, keywords={keywords}")
