"""
LLMClient 单元测试
"""
import json
import pytest
from unittest.mock import MagicMock, patch
from src.core.llm_client import LLMClient


class TestLLMClientInit:
    @patch("src.core.llm_client.OpenAI")
    def test_init_with_api_key(self, mock_openai):
        client = LLMClient(api_key="test_key")
        assert client.api_key == "test_key"
        assert client.model == "deepseek-chat"
        mock_openai.assert_called_once()

    @patch("src.core.llm_client.OpenAI")
    def test_init_with_custom_model(self, mock_openai):
        client = LLMClient(api_key="test_key", model="custom-model")
        assert client.model == "custom-model"


class TestLLMClientChat:
    @patch("src.core.llm_client.OpenAI")
    def test_chat_returns_text(self, mock_openai):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello"
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        client = LLMClient(api_key="test_key")
        result = client.chat(messages=[{"role": "user", "content": "Hi"}])
        assert result == "Hello"

    @patch("src.core.llm_client.OpenAI")
    def test_chat_with_system_prompt(self, mock_openai):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        client = LLMClient(api_key="test_key")
        client.chat(messages=[{"role": "user", "content": "Hi"}], system_prompt="You are helpful")
        call_args = mock_openai.return_value.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are helpful"

    @patch("src.core.llm_client.OpenAI")
    def test_chat_handles_none_content(self, mock_openai):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        client = LLMClient(api_key="test_key")
        result = client.chat(messages=[{"role": "user", "content": "Hi"}])
        assert result == ""

    @patch("src.core.llm_client.OpenAI")
    def test_chat_handles_error(self, mock_openai):
        from openai import OpenAIError
        mock_openai.return_value.chat.completions.create.side_effect = OpenAIError("API error")

        client = LLMClient(api_key="test_key")
        result = client.chat(messages=[{"role": "user", "content": "Hi"}])
        assert "API error" in result


class TestLLMClientChatJson:
    @patch("src.core.llm_client.OpenAI")
    def test_chat_json_parses_valid_json(self, mock_openai):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"key": "value"}'
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        client = LLMClient(api_key="test_key")
        result = client.chat_json(user_message="test")
        assert result == {"key": "value"}

    @patch("src.core.llm_client.OpenAI")
    def test_chat_json_strips_markdown(self, mock_openai):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '```json\n{"key": "value"}\n```'
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        client = LLMClient(api_key="test_key")
        result = client.chat_json(user_message="test")
        assert result == {"key": "value"}

    @patch("src.core.llm_client.OpenAI")
    def test_chat_json_returns_empty_on_invalid(self, mock_openai):
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not json"
        mock_openai.return_value.chat.completions.create.return_value = mock_response

        client = LLMClient(api_key="test_key")
        result = client.chat_json(user_message="test")
        assert result == {}
