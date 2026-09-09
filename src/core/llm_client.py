"""
LLM 客户端封装 - 统一调用 DeepSeek API
"""
import os
import json
import logging
from typing import Optional, List, Dict, Any, Callable
from openai import OpenAI, OpenAIError

logger = logging.getLogger(__name__)


class LLMClient:
    """LLM 客户端 - 封装 DeepSeek API 调用"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        timeout: int = 30,
        max_tokens: int = 4000,
        temperature: float = 0.7,
    ):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.temperature = temperature

        if not self.api_key:
            logger.warning("DEEPSEEK_API_KEY 未设置，LLM 调用将失败")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )
        logger.info(f"LLM Client 初始化: model={self.model}")

    def chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """
        发送对话请求，返回文本响应

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            system_prompt: 系统提示（会插入到 messages 最前面）
            temperature: 温度（覆盖默认值）
            max_tokens: 最大 token 数（覆盖默认值）

        Returns:
            LLM 返回的文本
        """
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
            )
            return response.choices[0].message.content or ""
        except OpenAIError as e:
            logger.error(f"LLM 调用失败: {e}")
            return f"[LLM 调用失败: {e}]"

    def stream_chat(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        on_thinking: Optional[Callable[[str], None]] = None,
        on_content: Optional[Callable[[str], None]] = None,
    ) -> str:
        """
        流式对话，支持 thinking 回调

        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            system_prompt: 系统提示
            temperature: 温度
            max_tokens: 最大 token 数
            on_thinking: thinking 内容回调（模型思考时触发）
            on_content: 内容片段回调（每个内容块触发）

        Returns:
            完整响应文本
        """
        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=full_messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                stream=True,
            )

            full_content = ""
            thinking_content = ""

            for chunk in response:
                delta = chunk.choices[0].delta
                reasoning = getattr(delta, 'reasoning_content', None) or getattr(delta, 'reasoning', None)
                content = getattr(delta, 'content', None)

                if reasoning:
                    thinking_content += reasoning
                    if on_thinking:
                        on_thinking(reasoning)
                elif content:
                    full_content += content
                    if on_content:
                        on_content(content)

            return full_content

        except OpenAIError as e:
            logger.error(f"LLM 流式调用失败: {e}")
            return f"[LLM 调用失败: {e}]"

    def chat_json(
        self,
        user_message: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
    ) -> Dict[str, Any]:
        """
        发送对话请求，期望返回 JSON 格式

        Args:
            user_message: 用户消息
            system_prompt: 系统提示
            temperature: 温度（默认较低以保证格式稳定）

        Returns:
            解析后的 JSON 字典
        """
        full_system = system_prompt or ""
        full_system += "\n\n请只返回 JSON 格式，不要包含其他内容。"

        messages = [{"role": "user", "content": user_message}]

        try:
            raw = self.chat(
                messages=messages,
                system_prompt=full_system,
                temperature=temperature,
            )
            return self._parse_json(raw)
        except Exception as e:
            logger.error(f"LLM JSON 调用失败: {e}")
            return {}

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """从 LLM 返回的文本中解析 JSON"""
        # 尝试直接解析
        text = text.strip()

        # 去除可能的 markdown 代码块
        if text.startswith("```"):
            text = text.split("```", 2)[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失败: {e}\n原始文本: {text[:200]}")
            return {}
