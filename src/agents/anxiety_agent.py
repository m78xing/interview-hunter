"""
焦虑缓解 Agent
"""
import logging
from typing import Optional, Callable

from src.core.llm_client import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """你是一个温暖的面试陪伴者。
- 理解用户的焦虑和压力
- 提供情感支持和鼓励
- 不要说教或讲大道理
- 适度共情，适度鼓励
- 如果用户情绪过于消极，建议寻求专业帮助
- 如果用户只是闲聊，保持轻松友好的氛围
- 可以适度引导用户进入学习状态，但不要强制"""


class AnxietyReliefAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client

    def chat(self, user_message: str, history: Optional[list] = None) -> str:
        messages = []
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        response = self.llm.chat(
            messages=messages,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.8,
        )
        logger.info(f"AnxietyReliefAgent responded")
        return response

    def chat_stream(
        self,
        user_message: str,
        history: Optional[list] = None,
        on_thinking: Optional[Callable[[str], None]] = None,
        on_content: Optional[Callable[[str], None]] = None,
    ) -> str:
        messages = []
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        response = self.llm.stream_chat(
            messages=messages,
            system_prompt=SYSTEM_PROMPT,
            temperature=0.8,
            on_thinking=on_thinking,
            on_content=on_content,
        )
        logger.info(f"AnxietyReliefAgent responded")
        return response
