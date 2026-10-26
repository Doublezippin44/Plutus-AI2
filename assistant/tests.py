import os
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase
from openai import AuthenticationError, RateLimitError

from .models import ChatMessage
from .openai_client import AIProviderError, ask_openai


class GroqClientTests(SimpleTestCase):
    @patch.dict(os.environ, {"GROQ_API_KEY": ""})
    def test_missing_key_is_explicit(self):
        with self.assertRaises(AIProviderError) as raised:
            ask_openai("What is a stock?")
        self.assertEqual(raised.exception.code, "missing_api_key")

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-not-real"}, clear=False)
    @patch("assistant.openai_client.OpenAI")
    def test_success(self, client_cls):
        client_cls.return_value.chat.completions.create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="  Hello  "))]
        )
        self.assertEqual(ask_openai("Hello"), "Hello")
        self.assertEqual(
            client_cls.call_args.kwargs["base_url"],
            "https://api.groq.com/openai/v1",
        )

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-not-real"}, clear=False)
    @patch("assistant.openai_client.OpenAI")
    def test_revoked_key_is_safe(self, client_cls):
        response = httpx.Response(
            401, request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        )
        client_cls.return_value.chat.completions.create.side_effect = AuthenticationError(
            "sensitive upstream detail", response=response, body={}
        )
        with self.assertRaises(AIProviderError) as raised:
            ask_openai("Hello")
        self.assertEqual(raised.exception.code, "invalid_api_key")
        self.assertNotIn("sensitive upstream detail", str(raised.exception))

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-not-real"}, clear=False)
    @patch("assistant.openai_client.OpenAI")
    def test_rate_limit_is_distinct(self, client_cls):
        response = httpx.Response(
            429, request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
        )
        client_cls.return_value.chat.completions.create.side_effect = RateLimitError(
            "retry later", response=response, body={}
        )
        with self.assertRaises(AIProviderError) as raised:
            ask_openai("Hello")
        self.assertEqual(raised.exception.code, "rate_limited")
        self.assertEqual(raised.exception.status_code, 429)


class ChatEndpointTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="groq-test-user", password="test-password-for-tests"
        )
        self.client.force_login(self.user)

    @patch("assistant.views.ask_openai")
    def test_provider_failure_returns_error_without_saving_chat(self, mocked_ai):
        mocked_ai.side_effect = AIProviderError(
            "AI authentication failed.", code="invalid_api_key", status_code=503
        )
        response = self.client.post(
            "/api/assistant/chat/",
            data='{"message":"Hello"}',
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], "invalid_api_key")
        self.assertEqual(ChatMessage.objects.count(), 0)
