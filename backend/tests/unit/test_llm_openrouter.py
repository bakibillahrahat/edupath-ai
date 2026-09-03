"""Tests for OpenRouterProvider: error classification, retry policy, and
structured output parsing."""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import httpx
import pytest
from pydantic import BaseModel

from app.core.exceptions import LLMError, LLMQuotaError
from app.infrastructure.llm.openrouter import (
    OpenRouterProvider,
    _is_non_retryable_client_error,
    _is_quota_error,
    _is_retryable,
    _is_transient_5xx,
)

_URL = "https://openrouter.ai/api/v1/chat/completions"


class SampleModel(BaseModel):
    name: str
    value: int


def _response(status_code: int, json_body: dict, headers: dict | None = None) -> httpx.Response:
    return httpx.Response(status_code, json=json_body, headers=headers or {}, request=httpx.Request("POST", _URL))


def _error_response(status_code: int, message: str = "boom", headers: dict | None = None) -> httpx.Response:
    return _response(status_code, {"error": {"message": message}}, headers=headers)


def _success_response(text: str, *, prompt_tokens=5, completion_tokens=7) -> httpx.Response:
    return _response(
        200,
        {
            "choices": [{"message": {"content": text}}],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        },
    )


@pytest.fixture
def mock_provider():
    provider = OpenRouterProvider()
    provider._client = MagicMock()
    return provider


# ---------------------------------------------------------------------------
# Classification helpers
# ---------------------------------------------------------------------------


def test_is_quota_error_detects_429() -> None:
    exc = httpx.HTTPStatusError("boom", request=httpx.Request("POST", _URL), response=_error_response(429))
    assert _is_quota_error(exc) is True


def test_is_quota_error_ignores_other_codes() -> None:
    exc = httpx.HTTPStatusError("boom", request=httpx.Request("POST", _URL), response=_error_response(500))
    assert _is_quota_error(exc) is False


def test_is_transient_5xx() -> None:
    for code, expected in [(500, True), (503, True), (429, False), (404, False)]:
        exc = httpx.HTTPStatusError("boom", request=httpx.Request("POST", _URL), response=_error_response(code))
        assert _is_transient_5xx(exc) is expected


def test_is_non_retryable_client_error() -> None:
    for code, expected in [(400, True), (401, True), (403, True), (404, True), (429, False), (503, False)]:
        exc = httpx.HTTPStatusError("boom", request=httpx.Request("POST", _URL), response=_error_response(code))
        assert _is_non_retryable_client_error(exc) is expected


def test_is_retryable_retries_429_and_5xx_excludes_4xx() -> None:
    def _exc(code):
        return httpx.HTTPStatusError("boom", request=httpx.Request("POST", _URL), response=_error_response(code))

    assert _is_retryable(_exc(429)) is True
    assert _is_retryable(_exc(400)) is False
    assert _is_retryable(_exc(404)) is False
    assert _is_retryable(_exc(503)) is True


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------


def test_generate_success_returns_text(mock_provider: OpenRouterProvider) -> None:
    mock_provider._client.post.return_value = _success_response("hello")

    result = mock_provider.generate("hi")

    assert result.text == "hello"
    assert result.usage.total_tokens == 12


def test_generate_404_does_not_retry_and_raises_llmerror(mock_provider: OpenRouterProvider) -> None:
    mock_provider._client.post.return_value = _error_response(404, "model missing")

    with pytest.raises(LLMError):
        mock_provider.generate("hi")

    assert mock_provider._client.post.call_count == 1


def test_generate_429_retries_and_raises_quota_error_when_exhausted(mock_provider: OpenRouterProvider) -> None:
    mock_provider._client.post.return_value = _error_response(429, "Quota exceeded", headers={"retry-after": "27"})

    with pytest.raises(LLMQuotaError) as exc_info:
        mock_provider.generate("hi")

    err = exc_info.value
    assert err.status_code == 429
    assert err.retry_after == 27
    assert err.provider == "openrouter"
    assert mock_provider._client.post.call_count == 4


def test_generate_429_then_success_succeeds(mock_provider: OpenRouterProvider) -> None:
    """First call 429, second attempt succeeds."""
    mock_provider._client.post.side_effect = [
        _error_response(429, "Rate limit"),
        _success_response("recovered text"),
    ]

    result = mock_provider.generate("hi")
    assert result.text == "recovered text"
    assert mock_provider._client.post.call_count == 2


def test_generate_5xx_retries_and_raises_when_exhausted(mock_provider: OpenRouterProvider) -> None:
    mock_provider._client.post.return_value = _error_response(503, "transient")

    with pytest.raises(LLMError):
        mock_provider.generate("hi")

    assert mock_provider._client.post.call_count == 4


def test_generate_5xx_then_success_succeeds(mock_provider: OpenRouterProvider) -> None:
    mock_provider._client.post.side_effect = [
        _error_response(503, "transient"),
        _success_response("ok"),
    ]

    result = mock_provider.generate("hi")
    assert result.text == "ok"
    assert mock_provider._client.post.call_count == 2


# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------


def test_generate_structured_with_plain_json(mock_provider: OpenRouterProvider) -> None:
    mock_provider._client.post.return_value = _success_response(json.dumps({"name": "test", "value": 123}))

    structured, _ = mock_provider.generate_structured("p", response_model=SampleModel)

    assert structured.name == "test"
    assert structured.value == 123


def test_generate_structured_with_markdown_fences(mock_provider: OpenRouterProvider) -> None:
    mock_provider._client.post.return_value = _success_response('```json\n{"name": "test", "value": 123}\n```')

    structured, _ = mock_provider.generate_structured("p", response_model=SampleModel)

    assert structured.name == "test"
    assert structured.value == 123


def test_generate_structured_sends_json_object_response_format(mock_provider: OpenRouterProvider) -> None:
    mock_provider._client.post.return_value = _success_response(json.dumps({"name": "n", "value": 1}))

    mock_provider.generate_structured("p", response_model=SampleModel)

    payload = mock_provider._client.post.call_args.kwargs["json"]
    assert payload["response_format"] == {"type": "json_object"}
    # The schema is spelled out in the prompt text (closed-book), not relied
    # on solely via response_format, since not every free model behind
    # openrouter/free supports strict json_schema mode.
    assert "value" in payload["messages"][0]["content"]


def test_generate_structured_empty_response(mock_provider: OpenRouterProvider) -> None:
    mock_provider._client.post.return_value = _success_response("")

    with pytest.raises(LLMError, match="OpenRouter returned an empty response"):
        mock_provider.generate_structured("p", response_model=SampleModel)


def test_generate_structured_invalid_json(mock_provider: OpenRouterProvider) -> None:
    mock_provider._client.post.return_value = _success_response('{"name": "test", "value": 123,}')

    with pytest.raises(LLMError, match="Invalid JSON response from OpenRouter"):
        mock_provider.generate_structured("p", response_model=SampleModel)


def test_generate_structured_validation_error(mock_provider: OpenRouterProvider) -> None:
    mock_provider._client.post.return_value = _success_response(json.dumps({"name": "test", "value": [1, 2, 3]}))

    with pytest.raises(LLMError, match="OpenRouter response failed Pydantic validation"):
        mock_provider.generate_structured("p", response_model=SampleModel)


def test_generate_structured_quota_error_propagates(mock_provider: OpenRouterProvider) -> None:
    mock_provider._client.post.return_value = _error_response(429, "Quota", headers={"retry-after": "5"})

    with pytest.raises(LLMQuotaError) as exc_info:
        mock_provider.generate_structured("p", response_model=SampleModel)

    assert exc_info.value.retry_after == 5


def test_embed_text_returns_embedding_values(mock_provider: OpenRouterProvider) -> None:
    embedding = [0.1] * 1536
    mock_provider._client.post.return_value = httpx.Response(
        200,
        json={"data": [{"embedding": embedding}]},
        request=httpx.Request("POST", _URL),
    )

    values = mock_provider.embed_text("hi")

    assert values == embedding
    payload = mock_provider._client.post.call_args.kwargs["json"]
    assert payload["input"] == "hi"
    assert payload["model"] == "openai/text-embedding-3-small"


def test_embed_text_raises_llmerror_when_response_missing_embedding(mock_provider: OpenRouterProvider) -> None:
    mock_provider._client.post.return_value = httpx.Response(
        200,
        json={"data": [{}]},
        request=httpx.Request("POST", _URL),
    )

    with pytest.raises(LLMError, match="embedding"):
        mock_provider.embed_text("hi")
