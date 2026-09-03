from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from app.core.config import settings
from app.core.exceptions import LLMError, LLMQuotaError
from app.core.logging import get_logger
from app.infrastructure.llm.base import LLMCallContext, LLMResult
from app.infrastructure.llm.usage import TokenUsage, estimate_cost_usd

T = TypeVar("T", bound=BaseModel)

_logger = get_logger(component="llm")


class TransientOpenRouterError(LLMError):
    """Raised for retryable OpenRouter payload errors like 504 abort, 502/503 upstream, or rate limits."""
    pass


# ---------------------------------------------------------------------------
# Error classification (OpenRouter is a REST API fronting many underlying
# models, so errors arrive as plain HTTP status codes rather than the
# google-genai SDK's typed exceptions).
# ---------------------------------------------------------------------------


def _is_quota_error(exc: BaseException) -> bool:
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code == 429


def _is_transient_5xx(exc: BaseException) -> bool:
    return isinstance(exc, httpx.HTTPStatusError) and 500 <= exc.response.status_code < 600


def _is_non_retryable_client_error(exc: BaseException) -> bool:
    return isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in {400, 401, 403, 404}


def _is_retryable(exc: BaseException) -> bool:
    """Tenacity predicate: retry transient 5xx errors, payload aborts, and 429 rate limit bursts
    with backoff."""
    if isinstance(exc, TransientOpenRouterError):
        return True
    if _is_non_retryable_client_error(exc):
        return False
    if _is_quota_error(exc):
        return True
    return _is_transient_5xx(exc)


def _extract_error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
    except ValueError:
        return response.text[:500]
    error = body.get("error") if isinstance(body, dict) else None
    if isinstance(error, dict) and error.get("message"):
        return str(error["message"])
    return response.text[:500]


def _extract_retry_after_seconds(response: httpx.Response) -> int | None:
    header = response.headers.get("retry-after")
    if header:
        try:
            return int(float(header))
        except ValueError:
            pass
    return None


def _build_quota_error(exc: httpx.HTTPStatusError, *, provider: str, model: str | None) -> LLMQuotaError:
    message = _extract_error_message(exc.response)
    return LLMQuotaError(
        f"OpenRouter rate limit exhausted for model {model or 'unknown'}: {message}",
        provider=provider,
        model=model,
        status_code=exc.response.status_code,
        retry_after=_extract_retry_after_seconds(exc.response) or 30,
        quota_message=message,
    )


def _log_retry_attempt(retry_state: RetryCallState) -> None:
    """Hook used by tenacity to log transient retries for observability."""
    ctx = retry_state.kwargs.get("context") if retry_state.kwargs else None
    fields = ctx.fields() if isinstance(ctx, LLMCallContext) else {}
    exc = retry_state.outcome.exception() if retry_state.outcome else None
    status_code = getattr(getattr(exc, "response", None), "status_code", None)
    _logger.warning(
        "openrouter_transient_retry",
        attempt=retry_state.attempt_number,
        next_attempt=retry_state.attempt_number + 1,
        next_sleep=round(retry_state.next_action.sleep, 2) if retry_state.next_action else None,
        status_code=status_code,
        error_type=exc.__class__.__name__ if exc else None,
        **fields,
    )


# ---------------------------------------------------------------------------
# Provider
# ---------------------------------------------------------------------------


class OpenRouterProvider:
    """Text generation and embedding provider backed by OpenRouter's
    OpenAI-compatible REST API. Defaults to ``openrouter/free`` for chat
    generation, while embeddings use a standard OpenRouter-compatible embedding
    model (such as ``openai/text-embedding-3-small``).
    """

    def __init__(self) -> None:
        self._client: httpx.Client | None = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                base_url=settings.openrouter_base_url,
                timeout=settings.openrouter_request_timeout_seconds,
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                    # Optional OpenRouter attribution headers; harmless if ignored.
                    "HTTP-Referer": "https://github.com/edupath-ai",
                    "X-Title": "EduPath AI",
                },
            )
        return self._client

    def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float | None = None,
        system_instruction: str | None = None,
        context: LLMCallContext | None = None,
    ) -> LLMResult:
        model_name = model or settings.openrouter_model
        ctx = context or LLMCallContext(purpose="generate")
        attempt_counter: dict[str, int] = {}

        try:
            body = self._chat_completion(
                model_name,
                prompt,
                temperature=temperature,
                system_instruction=system_instruction,
                response_format=None,
                context=ctx,
                attempt_counter=attempt_counter,
            )
        except LLMError:
            raise
        except httpx.HTTPStatusError as exc:
            if _is_quota_error(exc):
                _logger.warning("openrouter_call_quota_exhausted", model=model_name, **ctx.fields())
                raise _build_quota_error(exc, provider="openrouter", model=model_name) from exc
            _logger.warning("openrouter_call_failed", model=model_name, error_type=exc.__class__.__name__, **ctx.fields())
            raise LLMError(f"OpenRouter request failed: {_extract_error_message(exc.response)}") from exc
        except httpx.HTTPError as exc:
            _logger.warning("openrouter_call_failed", model=model_name, error_type=exc.__class__.__name__, **ctx.fields())
            raise LLMError(f"OpenRouter request failed: {exc}") from exc

        text, usage = self._parse_completion(body, model_name)
        _logger.info("openrouter_call_success", model=model_name, total_tokens=usage.total_tokens, **ctx.fields())
        return LLMResult(text=text, usage=usage)

    def generate_structured(
        self,
        prompt: str,
        *,
        response_model: type[T],
        model: str | None = None,
        temperature: float | None = None,
        system_instruction: str | None = None,
        context: LLMCallContext | None = None,
    ) -> tuple[T, LLMResult]:
        model_name = model or settings.openrouter_model
        ctx = context or LLMCallContext()
        if not ctx.purpose:
            ctx.purpose = response_model.__name__
        attempt_counter: dict[str, int] = {}

        # openrouter/free rotates across underlying free models, and not all
        # of them reliably support strict json_schema mode -- so schema
        # guidance is spelled out in the prompt text (closed-book style,
        # same trick used in app/tools/page_extractor.py) rather than relied
        # on solely via response_format, and the broader "json_object" mode
        # is used for the wire-format hint instead of strict json_schema.
        schema_instruction = (
            f"{system_instruction or ''}\n\n"
            "Output must be a single valid JSON object (no markdown fences, no commentary) "
            f"matching this JSON Schema exactly:\n{json.dumps(response_model.model_json_schema())}"
        ).strip()

        last_error = None
        for attempt in range(1, 4):
            try:
                body = self._chat_completion(
                    model_name,
                    prompt,
                    temperature=temperature,
                    system_instruction=schema_instruction,
                    response_format={"type": "json_object"},
                    context=ctx,
                    attempt_counter=attempt_counter,
                )
            except LLMError:
                raise
            except httpx.HTTPStatusError as exc:
                if _is_quota_error(exc):
                    _logger.warning("openrouter_call_quota_exhausted", model=model_name, **ctx.fields())
                    raise _build_quota_error(exc, provider="openrouter", model=model_name) from exc
                _logger.warning("openrouter_call_failed", model=model_name, error_type=exc.__class__.__name__, **ctx.fields())
                raise LLMError(
                    f"OpenRouter structured request failed for {response_model.__name__}: {_extract_error_message(exc.response)}"
                ) from exc
            except httpx.HTTPError as exc:
                _logger.warning("openrouter_call_failed", model=model_name, error_type=exc.__class__.__name__, **ctx.fields())
                raise LLMError(
                    f"OpenRouter structured request failed for {response_model.__name__}: {exc}"
                ) from exc

            raw_text, usage = self._parse_completion(body, model_name)
            if not raw_text.strip():
                if attempt < 3:
                    continue
                raise LLMError(f"OpenRouter returned an empty response for {response_model.__name__}.")

            result = LLMResult(text=raw_text, usage=usage)
            _logger.info("openrouter_call_success", model=model_name, total_tokens=usage.total_tokens, **ctx.fields())

            text_to_parse = self._strip_code_fence(raw_text)

            try:
                return response_model.model_validate_json(text_to_parse), result
            except json.JSONDecodeError as exc:
                last_error = exc
                _logger.warning(
                    "openrouter_structured_parse_retry",
                    attempt=attempt,
                    model=model_name,
                    error=str(exc)[:150],
                    **ctx.fields(),
                )
                if attempt == 3:
                    error_msg = f"Invalid JSON response from OpenRouter for {response_model.__name__}. "
                    error_msg += f"Response: ```{text_to_parse[:500]}...```"
                    raise LLMError(error_msg) from exc
            except ValidationError as exc:
                last_error = exc
                is_json_error = any((err.get("type") or "").startswith("json_") for err in exc.errors())
                _logger.warning(
                    "openrouter_structured_parse_retry",
                    attempt=attempt,
                    model=model_name,
                    error=str(exc)[:150],
                    **ctx.fields(),
                )
                if attempt == 3:
                    if is_json_error:
                        error_msg = f"Invalid JSON response from OpenRouter for {response_model.__name__}. "
                        error_msg += f"Response: ```{text_to_parse[:500]}...```"
                        raise LLMError(error_msg) from exc
                    error_msg = f"OpenRouter response failed Pydantic validation for {response_model.__name__}. "
                    error_msg += f"Response: ```{text_to_parse[:500]}...```. "
                    error_msg += f"Validation Error: {exc}"
                    raise LLMError(error_msg) from exc

        raise LLMError(f"Failed to generate structured response for {response_model.__name__}: {last_error}")

    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_exponential_jitter(initial=2.0, max=12, jitter=1.0),
        stop=stop_after_attempt(4),
        reraise=True,
        before_sleep=_log_retry_attempt,
    )
    def _chat_completion(
        self,
        model_name: str,
        prompt: str,
        *,
        temperature: float | None,
        system_instruction: str | None,
        response_format: dict | None,
        context: LLMCallContext | None = None,
        attempt_counter: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        if attempt_counter is not None:
            attempt_counter["count"] = attempt_counter.get("count", 0) + 1
        attempt = attempt_counter.get("count", 1) if attempt_counter is not None else 1
        fields = context.fields() if isinstance(context, LLMCallContext) else {}
        _logger.info("openrouter_chat_completion_attempt", model=model_name, attempt=attempt, **fields)

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": temperature if temperature is not None else settings.openrouter_temperature,
            "max_tokens": 4096,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        response = self.client.post("/chat/completions", json=payload)
        response.raise_for_status()
        data = response.json()

        # Handle OpenRouter 200 responses containing an error block (e.g. 504 abort / timeout)
        if isinstance(data, dict) and "error" in data and not data.get("choices"):
            err = data["error"]
            err_code = err.get("code") if isinstance(err, dict) else None
            err_msg = err.get("message", "") if isinstance(err, dict) else str(err)
            if err_code in {504, 503, 502, 500, 429} or "aborted" in err_msg.lower() or "timeout" in err_msg.lower():
                _logger.warning("openrouter_transient_payload_error", code=err_code, message=err_msg, model=model_name)
                raise TransientOpenRouterError(f"OpenRouter transient error ({err_code}): {err_msg}")
            raise LLMError(f"OpenRouter returned an error: {err_msg}")

        if not data.get("choices"):
            raise TransientOpenRouterError(f"OpenRouter response for {model_name} contained no choices: {data}")

        return data

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        text_to_parse = text.strip()
        pattern = r"```(?:json)?\s*([\s\S]*?)\s*```"
        match = re.search(pattern, text_to_parse)
        if match:
            return match.group(1).strip()
        start_brace = text_to_parse.find("{")
        start_bracket = text_to_parse.find("[")
        start = -1
        if start_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
            start = start_brace
            end = text_to_parse.rfind("}")
        elif start_bracket != -1:
            start = start_bracket
            end = text_to_parse.rfind("]")
        if start != -1 and end != -1 and end > start:
            return text_to_parse[start : end + 1].strip()
        return text_to_parse

    def _parse_completion(self, body: dict[str, Any], model_name: str) -> tuple[str, TokenUsage]:
        choices = body.get("choices") or []
        if not choices:
            raise LLMError(f"OpenRouter response for {model_name} contained no choices: {body}")
        text = ((choices[0].get("message") or {}).get("content")) or ""

        usage_block = body.get("usage") or {}
        input_tokens = int(usage_block.get("prompt_tokens", 0) or 0)
        output_tokens = int(usage_block.get("completion_tokens", 0) or 0)
        total_tokens = int(usage_block.get("total_tokens", 0) or (input_tokens + output_tokens))
        usage = TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimate_cost_usd(model_name, input_tokens, output_tokens),
            usage_available=bool(usage_block),
        )
        return text, usage

    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_exponential_jitter(initial=1.5, max=10, jitter=1.0),
        stop=stop_after_attempt(3),
        reraise=True,
        before_sleep=_log_retry_attempt,
    )
    def _post_embedding(self, model_name: str, text: str) -> dict[str, Any]:
        response = self.client.post(
            "/embeddings",
            json={
                "model": model_name,
                "input": text,
            },
        )
        response.raise_for_status()
        return response.json()

    def embed_text(self, text: str, *, model: str | None = None) -> list[float]:
        model_name = model or settings.embedding_model
        try:
            body = self._post_embedding(model_name, text)
        except httpx.HTTPStatusError as exc:
            if _is_quota_error(exc):
                raise _build_quota_error(exc, provider="openrouter", model=model_name) from exc
            raise LLMError(f"OpenRouter embedding request failed: {_extract_error_message(exc.response)}") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"OpenRouter embedding request failed: {exc}") from exc

        data = body.get("data") or []
        if not data:
            raise LLMError(f"OpenRouter embedding response missing data for model {model_name}")

        embedding = (data[0] or {}).get("embedding")
        if not embedding:
            raise LLMError(f"OpenRouter embedding response missing embedding values for model {model_name}")

        if len(embedding) != settings.embedding_dimensions:
            raise LLMError(
                f"OpenRouter embedding dimension mismatch: expected {settings.embedding_dimensions}, got {len(embedding)}"
            )

        return [float(value) for value in embedding]


@lru_cache
def get_openrouter_provider() -> OpenRouterProvider:
    return OpenRouterProvider()

OpenRouterClient = OpenRouterProvider
__all__ = [
    "OpenRouterProvider",
    "OpenRouterClient",
    "TransientOpenRouterError",
    "get_openrouter_provider",
]
