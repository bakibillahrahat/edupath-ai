from __future__ import annotations

import httpx
import pytest

from app.core.exceptions import LLMError
from app.modules.ai_orchestration.tools.page_extractor import (
    PageExtractorTool,
    _ExtractedEntity,
    _PageExtractionOutput,
)

_SAMPLE_HTML = """
<html>
<head><script>console.log('nav junk')</script></head>
<body>
<nav><a href="/about">About</a></nav>
<main>
<h1>Faculty Directory</h1>
<div>
  <a href="https://cs.example.edu/~ashton/">Ashton Anderson</a> Associate Professor, Room BA 100
  <a href="https://cs.example.edu/~bonner/">Anthony Bonner</a> Professor, Room BA 200
</div>
</main>
</body>
</html>
"""


class FakeResponse:
    def __init__(self, text: str, status_code: int = 200) -> None:
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=None, response=self)


class FakeHTTPClient:
    def __init__(self, text: str = _SAMPLE_HTML, raise_exc: Exception | None = None) -> None:
        self._text = text
        self._raise_exc = raise_exc
        self.requested_urls: list[str] = []

    async def get(self, url, follow_redirects=True):
        self.requested_urls.append(url)
        if self._raise_exc:
            raise self._raise_exc
        return FakeResponse(self._text)

    async def aclose(self):
        pass


class FakeProvider:
    def __init__(self, entities: list[_ExtractedEntity]) -> None:
        self._entities = entities
        self.prompts: list[str] = []

    def generate_structured(self, prompt, *, response_model, model=None, context=None):
        self.prompts.append(prompt)
        return _PageExtractionOutput(entities=self._entities), None


class FailingProvider:
    def generate_structured(self, prompt, *, response_model, model=None, context=None):
        raise LLMError("extraction unavailable")


@pytest.mark.asyncio
async def test_fetch_and_extract_maps_entities_to_real_links():
    client = FakeHTTPClient()
    provider = FakeProvider([
        _ExtractedEntity(name="Ashton Anderson", link_index=1, detail="Associate Professor"),
        _ExtractedEntity(name="Anthony Bonner", link_index=2, detail="Professor"),
    ])
    tool = PageExtractorTool(client=client, provider=provider)

    response = await tool.fetch_and_extract(
        "https://cs.example.edu/people/faculty-directory",
        tool_name="faculty_directory_search",
        entity_description="Extract faculty members.",
    )

    assert response.tool_status == "available"
    assert len(response.results) == 2
    by_name = {r.title: r for r in response.results}
    assert by_name["Ashton Anderson"].source.url == "https://cs.example.edu/~ashton/"
    assert by_name["Anthony Bonner"].source.url == "https://cs.example.edu/~bonner/"
    assert by_name["Ashton Anderson"].source.source == "official_website"


@pytest.mark.asyncio
async def test_fetch_and_extract_never_invents_a_url_for_unlinked_entity():
    client = FakeHTTPClient()
    provider = FakeProvider([_ExtractedEntity(name="Someone With No Link", link_index=None)])
    tool = PageExtractorTool(client=client, provider=provider)

    response = await tool.fetch_and_extract(
        "https://cs.example.edu/people", tool_name="faculty_directory_search", entity_description="Extract faculty.",
    )

    # Falls back to the page URL itself -- never a fabricated per-person URL.
    assert response.results[0].source.url == "https://cs.example.edu/people"


@pytest.mark.asyncio
async def test_fetch_and_extract_ignores_out_of_range_link_index():
    client = FakeHTTPClient()
    provider = FakeProvider([_ExtractedEntity(name="Hallucinated Index", link_index=9999)])
    tool = PageExtractorTool(client=client, provider=provider)

    response = await tool.fetch_and_extract(
        "https://cs.example.edu/people", tool_name="faculty_directory_search", entity_description="Extract faculty.",
    )

    assert response.results[0].source.url == "https://cs.example.edu/people"


@pytest.mark.asyncio
async def test_fetch_failure_reports_unavailable_not_a_crash():
    client = FakeHTTPClient(raise_exc=httpx.ConnectTimeout("timed out"))
    tool = PageExtractorTool(client=client, provider=FakeProvider([]))

    response = await tool.fetch_and_extract(
        "https://unreachable.example.edu", tool_name="faculty_directory_search", entity_description="Extract faculty.",
    )

    assert response.tool_status == "unavailable"
    assert response.results == []


@pytest.mark.asyncio
async def test_llm_extraction_failure_reports_unavailable_not_a_crash():
    client = FakeHTTPClient()
    tool = PageExtractorTool(client=client, provider=FailingProvider())

    response = await tool.fetch_and_extract(
        "https://cs.example.edu/people", tool_name="faculty_directory_search", entity_description="Extract faculty.",
    )

    assert response.tool_status == "unavailable"
    assert "Extraction unavailable" in response.notes[0]


@pytest.mark.asyncio
async def test_js_only_page_with_no_visible_text_reports_unavailable():
    client = FakeHTTPClient(text="<html><body><script>renderApp()</script></body></html>")
    tool = PageExtractorTool(client=client, provider=FakeProvider([]))

    response = await tool.fetch_and_extract(
        "https://js-heavy.example.edu", tool_name="faculty_directory_search", entity_description="Extract faculty.",
    )

    assert response.tool_status == "unavailable"
    assert response.results == []


@pytest.mark.asyncio
async def test_extra_metadata_is_merged_into_every_result():
    client = FakeHTTPClient()
    provider = FakeProvider([_ExtractedEntity(name="Ashton Anderson", link_index=1)])
    tool = PageExtractorTool(client=client, provider=provider)

    response = await tool.fetch_and_extract(
        "https://cs.example.edu/people/faculty-directory", tool_name="faculty_directory_search",
        entity_description="Extract faculty.", extra_metadata={"university": "Example University"},
    )

    assert response.results[0].metadata["university"] == "Example University"
    assert response.results[0].metadata["page_url"] == "https://cs.example.edu/people/faculty-directory"


@pytest.mark.asyncio
async def test_extraction_prompt_includes_real_links_not_fabricated_ones():
    client = FakeHTTPClient()
    provider = FakeProvider([])
    tool = PageExtractorTool(client=client, provider=provider)

    await tool.fetch_and_extract(
        "https://cs.example.edu/people/faculty-directory", tool_name="faculty_directory_search",
        entity_description="Extract faculty.",
    )

    prompt = provider.prompts[0]
    assert "https://cs.example.edu/~ashton/" in prompt
    assert "https://cs.example.edu/~bonner/" in prompt
    assert "never write a URL yourself" in prompt
