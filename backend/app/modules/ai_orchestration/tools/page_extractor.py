from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.exceptions import LLMError
from app.infrastructure.llm.base import LLMCallContext
from app.infrastructure.llm.openrouter import get_openrouter_provider
from app.modules.ai_orchestration.schemas import ToolSearchResponse, ToolSearchResult, ToolSource

_USER_AGENT = "Mozilla/5.0 (compatible; EduPathAI/1.0; +https://github.com/edupath-ai)"
_MAX_TEXT_CHARS = 8000
_MAX_LINKS = 150


class _ExtractedEntity(BaseModel):
    name: str
    link_index: int | None = None
    detail: str | None = None


class _PageExtractionOutput(BaseModel):
    entities: list[_ExtractedEntity] = Field(default_factory=list)


class PageExtractorTool:
    """Fetches one real page and extracts real entities from it via a
    closed-book LLM extraction constrained to that page's own text and
    links -- never asked to reproduce a URL itself, only to reference a
    real link by index. This is how EduPath AI discovers professors and
    universities without a web-search API: targeted, sourced scraping
    instead of asking the model to recall facts from training data.
    """

    def __init__(self, client: httpx.AsyncClient | None = None, provider=None) -> None:
        self._client = client
        self._provider = provider or get_openrouter_provider()

    async def fetch_and_extract(
        self,
        url: str,
        *,
        tool_name: str,
        entity_description: str,
        context: LLMCallContext | None = None,
        extra_metadata: dict | None = None,
    ) -> ToolSearchResponse:
        try:
            html = await self._fetch(url)
        except httpx.HTTPError as exc:
            return ToolSearchResponse(
                tool_name=tool_name, query=url, results=[], tool_status="unavailable",
                notes=[f"Could not fetch {url}: {type(exc).__name__}"],
            )

        text, links = self._parse(html, base_url=url)
        if not text.strip():
            return ToolSearchResponse(
                tool_name=tool_name, query=url, results=[], tool_status="unavailable",
                notes=[f"No extractable text on {url} (likely JavaScript-rendered content)."],
            )

        try:
            extraction = self._extract(text, links, entity_description=entity_description, context=context)
        except LLMError as exc:
            return ToolSearchResponse(
                tool_name=tool_name, query=url, results=[], tool_status="unavailable",
                notes=[f"Extraction unavailable: {exc}"],
            )

        retrieved_at = datetime.now(UTC)
        results: list[ToolSearchResult] = []
        for entity in extraction.entities:
            if not entity.name.strip():
                continue
            resolved_url = None
            if entity.link_index is not None and 0 <= entity.link_index < len(links):
                resolved_url = links[entity.link_index][1]
            results.append(
                ToolSearchResult(
                    title=entity.name.strip(),
                    description=entity.detail,
                    source=ToolSource(source="official_website", url=resolved_url or url, retrieved_at=retrieved_at, confidence=0.75),
                    metadata={"page_url": url, **(extra_metadata or {})},
                )
            )

        return ToolSearchResponse(tool_name=tool_name, query=url, results=results)

    async def _fetch(self, url: str) -> str:
        client = self._client or httpx.AsyncClient(timeout=settings.search_timeout_seconds, headers={"User-Agent": _USER_AGENT})
        close_client = self._client is None
        try:
            response = await self._get_with_retry(client, url)
            return response.text
        finally:
            if close_client:
                await client.aclose()

    @retry(
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError)),
        wait=wait_exponential(multiplier=0.25, min=0.25, max=2), stop=stop_after_attempt(3), reraise=True,
    )
    async def _get_with_retry(self, client: httpx.AsyncClient, url: str) -> httpx.Response:
        response = await client.get(url, follow_redirects=True)
        response.raise_for_status()
        return response

    def _parse(self, html: str, *, base_url: str) -> tuple[str, list[tuple[str, str]]]:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)[:_MAX_TEXT_CHARS]

        links: list[tuple[str, str]] = []
        for anchor in soup.find_all("a", href=True):
            label = anchor.get_text(strip=True)
            if not label:
                continue
            href = urljoin(base_url, anchor["href"])
            if not href.startswith(("http://", "https://")):
                continue
            links.append((label, href))
            if len(links) >= _MAX_LINKS:
                break

        return text, links

    def _extract(
        self, text: str, links: list[tuple[str, str]], *, entity_description: str, context: LLMCallContext | None
    ) -> _PageExtractionOutput:
        link_lines = "\n".join(f"[{index}] {label} -> {href}" for index, (label, href) in enumerate(links))
        prompt = f"""
You are extracting real entities that are ACTUALLY PRESENT on this fetched web page. Use ONLY the
page text and link list below -- do not use any outside knowledge, and do not invent an entity
that isn't genuinely represented in this content.

Task: {entity_description}

Page text:
{text}

Links found on this page (reference an entity's link by its index; never write a URL yourself):
{link_lines}

For each entity you find, return its name and, if one of the links above clearly corresponds to
it, that link's index (else null). Omit anything you are not reasonably confident is a real entry
on this page. Return an empty list if nothing qualifies.
"""
        structured, _ = self._provider.generate_structured(
            prompt, response_model=_PageExtractionOutput, context=context,
        )
        return structured
