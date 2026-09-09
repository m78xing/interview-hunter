"""
Context Manager - 上下文管理，处理超长会话摘要
"""
import logging
from typing import Optional

from src.core.context_store import ContextStore
from src.core.llm_client import LLMClient

logger = logging.getLogger(__name__)

SUMMARIZE_PROMPT = """将以下对话压缩为简洁的摘要，保留关键信息：

{turns}

摘要格式：
- 用户关注的知识点：xxx
- 用户修改过的配置：xxx
- 已完成的学习内容：xxx"""


class ContextManager:
    def __init__(self, context_store: ContextStore, llm_client: LLMClient, max_turns: int = 10, summary_threshold: int = 20):
        self.context_store = context_store
        self.llm = llm_client
        self.max_turns = max_turns
        self.summary_threshold = summary_threshold

    def get_context(self, session_id: str) -> str:
        history = self.context_store.load_latest_context(session_id)
        if not history:
            return ""

        chat_history = history.get("chat_history", [])

        if len(chat_history) > self.summary_threshold:
            old_turns = chat_history[:-self.max_turns]
            summary = self._summarize_turns(old_turns)

            new_history = {
                "summary": summary,
                "chat_history": chat_history[-self.max_turns:],
                "source": "chat",
            }
            self.context_store.save_context(
                session_id,
                new_history,
                version=history.get("version", 0) + 1,
            )
            return f"[历史摘要]\n{summary}\n\n[最近对话]\n{self._format_turns(chat_history[-self.max_turns:])}"

        recent = chat_history[-self.max_turns:] if len(chat_history) > self.max_turns else chat_history
        return self._format_turns(recent)

    def save_turn(self, session_id: str, role: str, content: str):
        history = self.context_store.load_latest_context(session_id)
        if history is None:
            history = {"chat_history": [], "source": "chat"}

        chat_history = history.get("chat_history") or history.get("metadata", {}).get("chat_history", [])
        chat_history.append({"role": role, "content": content})

        if "metadata" in history:
            history["metadata"]["chat_history"] = chat_history
        else:
            history["chat_history"] = chat_history

        self.context_store.save_context(
            session_id,
            history,
            version=history.get("version", 0) + 1,
        )

    def _summarize_turns(self, turns: list) -> str:
        formatted = self._format_turns(turns)
        return self.llm.chat(
            messages=[{"role": "user", "content": SUMMARIZE_PROMPT.format(turns=formatted)}],
            temperature=0.3,
        )

    def _format_turns(self, turns: list) -> str:
        parts = []
        for t in turns:
            role = "用户" if t.get("role") == "user" else "助手"
            parts.append(f"{role}: {t.get('content', '')}")
        return "\n".join(parts)

    def list_all_sessions(self) -> list:
        sessions = []
        for session_id in self.context_store.list_sessions():
            manifest = self.context_store.manifests.get(session_id)
            if not manifest:
                continue
            latest = manifest.get_latest_snapshot()
            if not latest:
                continue
            chat_history = latest.metadata.get("chat_history", [])
            sessions.append({
                "session_id": session_id,
                "created_at": latest.created_at,
                "summary": latest.summary,
                "message_count": len(chat_history),
                "source": latest.source,
            })
        sessions.sort(key=lambda x: x["created_at"], reverse=True)
        return sessions

    def load_session_messages(self, session_id: str) -> list:
        history = self.context_store.load_latest_context(session_id)
        if not history:
            return []
        return history.get("chat_history", []) or history.get("metadata", {}).get("chat_history", [])
