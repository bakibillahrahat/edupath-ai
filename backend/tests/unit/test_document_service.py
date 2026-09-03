from __future__ import annotations

import io
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import docx
import pytest

import app.modules.sop.document_service as document_module
from app.core.exceptions import LLMError
from app.modules.sop.document_service import DocumentService, DocumentValidationError, _chunk_text, _extract_text


def _build_docx_bytes(paragraphs: list[str]) -> bytes:
    document = docx.Document()
    for paragraph in paragraphs:
        document.add_paragraph(paragraph)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_extract_text_from_txt():
    assert _extract_text("resume.txt", b"Hello world") == "Hello world"


def test_extract_text_from_docx():
    raw = _build_docx_bytes(["First paragraph.", "Second paragraph."])
    text = _extract_text("cv.docx", raw)
    assert "First paragraph." in text
    assert "Second paragraph." in text


def test_extract_text_rejects_unsupported_extension():
    with pytest.raises(DocumentValidationError):
        _extract_text("resume.exe", b"whatever")


def test_extract_text_pdf_uses_pypdf(monkeypatch):
    class FakePage:
        def extract_text(self):
            return "PDF page text"

    class FakeReader:
        def __init__(self, stream):
            self.pages = [FakePage(), FakePage()]

    monkeypatch.setattr(document_module, "PdfReader", FakeReader)
    text = _extract_text("transcript.pdf", b"%PDF-fake-bytes")
    assert text == "PDF page text\nPDF page text"


def test_chunk_text_splits_long_text_with_overlap():
    text = "x" * 2500
    chunks = _chunk_text(text, size=1000, overlap=150)

    assert len(chunks) == 3
    # consecutive chunks overlap
    assert chunks[0][-150:] == chunks[1][:150]


def test_chunk_text_empty_input_returns_no_chunks():
    assert _chunk_text("") == []
    assert _chunk_text("   ") == []


def test_chunk_text_short_text_returns_single_chunk():
    assert _chunk_text("short text") == ["short text"]


class FakeProvider:
    def __init__(self, fail_embeddings: bool = False) -> None:
        self.fail_embeddings = fail_embeddings
        self.embed_calls: list[str] = []

    def embed_text(self, text, *, model=None):
        self.embed_calls.append(text)
        if self.fail_embeddings:
            raise LLMError("embeddings unavailable")
        return [0.1] * 1536


class FakeDocumentRepository:
    def __init__(self) -> None:
        self.created = None
        self.chunks_added = []

    async def create(self, session, document):
        document.id = uuid4()
        self.created = document
        return document

    async def get(self, session, document_id):
        return SimpleNamespace(
            id=document_id, profile_id=self.created.profile_id, filename=self.created.filename,
            document_type=self.created.document_type, chunks=self.chunks_added,
            created_at=datetime.now(UTC),
        )


@pytest.mark.asyncio
async def test_upload_extracts_chunks_and_embeds_each_one():
    provider = FakeProvider()
    repository = FakeDocumentRepository()
    service = DocumentService(repository=repository, provider=provider)

    class FakeSession:
        def add(self, chunk):
            repository.chunks_added.append(chunk)

        async def commit(self):
            pass

        async def refresh(self, obj):
            pass

    profile_id = uuid4()
    result = await service.upload(
        FakeSession(), profile_id=profile_id, filename="cv.txt", document_type="cv", raw=b"Some resume content."
    )

    assert result.filename == "cv.txt"
    assert result.document_type == "cv"
    assert result.chunk_count == 1
    assert len(provider.embed_calls) == 1


@pytest.mark.asyncio
async def test_upload_rejects_oversized_file(monkeypatch):
    monkeypatch.setattr(document_module.settings, "max_document_size_mb", 0.000001)  # ~1 byte
    service = DocumentService(repository=FakeDocumentRepository(), provider=FakeProvider())

    with pytest.raises(DocumentValidationError):
        await service.upload(SimpleNamespace(), profile_id=uuid4(), filename="cv.txt", document_type="cv", raw=b"too big for the limit")


@pytest.mark.asyncio
async def test_upload_still_succeeds_when_embeddings_unavailable():
    """A document should remain usable (e.g. via content_text) even if the
    embedding provider is temporarily down -- upload must not fail outright."""
    provider = FakeProvider(fail_embeddings=True)
    repository = FakeDocumentRepository()
    service = DocumentService(repository=repository, provider=provider)

    class FakeSession:
        def add(self, chunk):
            repository.chunks_added.append(chunk)

        async def commit(self):
            pass

        async def refresh(self, obj):
            pass

    result = await service.upload(
        FakeSession(), profile_id=uuid4(), filename="cv.txt", document_type="cv", raw=b"Some resume content."
    )

    assert result.chunk_count == 1
    assert repository.chunks_added[0].embedding is None


@pytest.mark.asyncio
async def test_retrieve_relevant_chunks_returns_empty_when_embeddings_unavailable():
    service = DocumentService(repository=FakeDocumentRepository(), provider=FakeProvider(fail_embeddings=True))

    chunks = await service.retrieve_relevant_chunks(SimpleNamespace(), uuid4(), "query text")

    assert chunks == []
