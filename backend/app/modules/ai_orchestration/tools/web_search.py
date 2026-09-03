from __future__ import annotations

from datetime import UTC, datetime

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.modules.ai_orchestration.schemas import ToolSearchResponse, ToolSearchResult, ToolSource


class WebSearchTool:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def search(self, query: str, limit: int = 5) -> ToolSearchResponse:
        if not settings.web_search_api_url:
            return ToolSearchResponse(
                tool_name="web_search",
                query=query,
                results=[],
                notes=["Web search API not configured."],
                tool_status="unavailable",
            )

        headers = {}
        if settings.web_search_api_key:
            headers["Authorization"] = f"Bearer {settings.web_search_api_key}"

        client = self._client or httpx.AsyncClient(timeout=settings.search_timeout_seconds, headers=headers)
        close_client = self._client is None

        try:
            payload = await self._request(client, query, limit)
        except (httpx.HTTPError, ValueError) as exc:
            return ToolSearchResponse(
                tool_name="web_search", query=query, results=[], tool_status="unavailable",
                notes=[f"Web search unavailable: {type(exc).__name__}"],
            )
        finally:
            if close_client:
                await client.aclose()

        results: list[ToolSearchResult] = []
        for item in payload.get("results", [])[:limit]:
            results.append(
                ToolSearchResult(
                    title=item.get("title", query),
                    description=item.get("description"),
                    source=ToolSource(
                        source="web_search",
                        url=item.get("url"),
                        retrieved_at=datetime.now(UTC),
                        confidence=float(item.get("confidence", 0.5)),
                    ),
                    metadata={k: v for k, v in item.items() if k not in {"title", "description", "url", "confidence"}},
                )
            )

        return ToolSearchResponse(tool_name="web_search", query=query, results=results)

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)),
        wait=wait_exponential(multiplier=0.25, min=0.25, max=2), stop=stop_after_attempt(3), reraise=True,
    )
    async def _request(self, client: httpx.AsyncClient, query: str, limit: int) -> dict:
        response = await client.get(settings.web_search_api_url, params={"q": query, "limit": limit})
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Search provider returned a non-object payload")
        return payload
