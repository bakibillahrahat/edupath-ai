from __future__ import annotations

from typing import Any

import requests
import streamlit as st

from api.exceptions import BackendError
from utils.config import (
    BACKEND_URL,
    CATALOG_SERVICE_URL,
    COUNSELING_SERVICE_URL,
    DOCUMENT_SERVICE_URL,
    MEMORY_SERVICE_URL,
    PROFILE_SERVICE_URL,
    REQUEST_TIMEOUT_SECONDS,
    TRACKER_SERVICE_URL,
    WORKFLOW_TIMEOUT_SECONDS,
)

__all__ = [
    "BackendError",
    "check_health",
    "check_health_cached",
    "get_auth_config",
    "dev_login",
    "get_current_user",
    "logout",
    "create_profile",
    "get_profile",
    "get_my_profile",
    "update_profile",
    "upload_document",
    "list_documents",
    "delete_document",
    "create_workflow",
    "analyze_counseling",
    "get_counseling_session",
    "get_workflow",
    "list_workflows",
    "approve_workflow",
    "reject_workflow",
    "get_workflow_agents",
    "get_workflow_messages",
    "get_workflow_logs",
    "download_workflow_export",
    "list_opportunities",
    "list_opportunities_cached",
    "get_opportunity",
    "list_memory",
    "generate_sop",
    "revise_sop",
    "get_sop",
    "list_sops",
    "list_applications",
    "create_application",
    "get_application",
    "update_application",
]


def _friendly_error_for_response(response: requests.Response) -> BackendError:
    try:
        body = response.json()
    except ValueError:
        body = {}

    if response.status_code == 429:
        retry_after = body.get("retry_after")
        suffix = f" Please try again in about {int(retry_after)} seconds." if retry_after else " Please try again shortly."
        return BackendError(
            "AI service is temporarily busy." + suffix,
            status_code=429,
            retry_after=retry_after,
        )

    if response.status_code >= 500:
        return BackendError("Something went wrong on the server. Please try again.", status_code=response.status_code)

    detail = body.get("detail") if isinstance(body, dict) else None
    if isinstance(detail, str):
        message = detail
    elif detail is not None:
        # FastAPI validation errors return detail as a list of error dicts.
        message = "The request could not be processed. Please check the form and try again."
    else:
        message = f"Request failed with status {response.status_code}."
    return BackendError(message, status_code=response.status_code)


def _auth_headers() -> dict[str, str]:
    token = st.session_state.get("auth_token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _request(method: str, path: str, *, service_url: str | None = None, timeout: float | None = None, **kwargs: Any) -> Any:
    base = service_url or BACKEND_URL
    url = f"{base}{path}"
    headers = {**_auth_headers(), **kwargs.pop("headers", {})}
    try:
        response = requests.request(method, url, timeout=timeout or REQUEST_TIMEOUT_SECONDS, headers=headers, **kwargs)
    except requests.exceptions.Timeout as exc:
        raise BackendError("The backend took too long to respond. The multi-agent workflow may still be processing in the background.", is_timeout=True) from exc
    except requests.exceptions.ConnectionError as exc:
        raise BackendError("Cannot connect to the EduPath-AI backend. Make sure the FastAPI server is running.", is_connection=True) from exc
    except requests.exceptions.RequestException as exc:
        raise BackendError("Could not reach the EduPath-AI backend. Please try again.", is_connection=True) from exc

    if not response.ok:
        raise _friendly_error_for_response(response)

    if not response.content:
        return None

    try:
        return response.json()
    except ValueError as exc:
        raise BackendError("Received an unexpected response from the backend.") from exc


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def check_health() -> dict:
    return _request("GET", "/health")


@st.cache_data(ttl=5, show_spinner=False)
def check_health_cached() -> dict:
    return check_health()


# ---------------------------------------------------------------------------
# Auth -- mirrors Identity & Profile Service
# ---------------------------------------------------------------------------


def get_auth_config() -> dict:
    return _request("GET", "/api/v1/auth/config", service_url=PROFILE_SERVICE_URL)


def dev_login(email: str, name: str | None) -> dict:
    params = {"email": email}
    if name:
        params["name"] = name
    return _request("GET", "/api/v1/auth/dev-login", params=params, service_url=PROFILE_SERVICE_URL)


def get_current_user() -> dict:
    return _request("GET", "/api/v1/auth/me", service_url=PROFILE_SERVICE_URL)


def logout() -> None:
    _request("POST", "/api/v1/auth/logout", service_url=PROFILE_SERVICE_URL)


# ---------------------------------------------------------------------------
# Profiles -- mirrors Identity & Profile Service
# ---------------------------------------------------------------------------


def create_profile(payload: dict) -> dict:
    return _request("POST", "/api/v1/profiles", json=payload, service_url=PROFILE_SERVICE_URL)


def get_profile(profile_id: str) -> dict:
    return _request("GET", f"/api/v1/profiles/{profile_id}", service_url=PROFILE_SERVICE_URL)


def get_my_profile() -> dict | None:
    return _request("GET", "/api/v1/profiles/me", service_url=PROFILE_SERVICE_URL)


def update_profile(profile_id: str, payload: dict) -> dict:
    return _request("PATCH", f"/api/v1/profiles/{profile_id}", json=payload, service_url=PROFILE_SERVICE_URL)


# ---------------------------------------------------------------------------
# Documents -- mirrors Document Studio & SOP Service
# ---------------------------------------------------------------------------


def upload_document(profile_id: str, document_type: str, filename: str, file_bytes: bytes) -> dict:
    return _request(
        "POST",
        "/api/v1/documents",
        data={"profile_id": profile_id, "document_type": document_type},
        files={"file": (filename, file_bytes)},
        service_url=DOCUMENT_SERVICE_URL,
    )


def list_documents(profile_id: str) -> list[dict]:
    return _request("GET", "/api/v1/documents", params={"profile_id": profile_id}, service_url=DOCUMENT_SERVICE_URL)


def delete_document(document_id: str) -> None:
    _request("DELETE", f"/api/v1/documents/{document_id}", service_url=DOCUMENT_SERVICE_URL)


# ---------------------------------------------------------------------------
# Workflows & AI Counseling -- mirrors Counseling & Workflow Service
# ---------------------------------------------------------------------------


def create_workflow(payload: dict) -> dict:
    return _request("POST", "/api/v1/workflows", json=payload, timeout=WORKFLOW_TIMEOUT_SECONDS, service_url=COUNSELING_SERVICE_URL)


def analyze_counseling(payload: dict) -> dict:
    return _request("POST", "/api/v1/counseling/analyze", json=payload, timeout=WORKFLOW_TIMEOUT_SECONDS, service_url=COUNSELING_SERVICE_URL)


def get_counseling_session(session_id: str) -> dict:
    return _request("GET", f"/api/v1/counseling/{session_id}", service_url=COUNSELING_SERVICE_URL)


def get_workflow(workflow_id: str) -> dict:
    return _request("GET", f"/api/v1/workflows/{workflow_id}", service_url=COUNSELING_SERVICE_URL)


def list_workflows(profile_id: str) -> list[dict]:
    return _request("GET", "/api/v1/workflows", params={"profile_id": profile_id}, service_url=COUNSELING_SERVICE_URL)


def approve_workflow(workflow_id: str, opportunity_id: str | None = None) -> dict:
    return _request("POST", f"/api/v1/workflows/{workflow_id}/approve", json={"opportunity_id": opportunity_id}, timeout=WORKFLOW_TIMEOUT_SECONDS, service_url=COUNSELING_SERVICE_URL)


def reject_workflow(workflow_id: str, opportunity_id: str | None = None) -> dict:
    return _request("POST", f"/api/v1/workflows/{workflow_id}/reject", json={"opportunity_id": opportunity_id}, timeout=WORKFLOW_TIMEOUT_SECONDS, service_url=COUNSELING_SERVICE_URL)


def get_workflow_agents(workflow_id: str) -> list[dict]:
    return _request("GET", f"/api/v1/workflows/{workflow_id}/agents", service_url=COUNSELING_SERVICE_URL)


def get_workflow_messages(workflow_id: str) -> list[dict]:
    return _request("GET", f"/api/v1/workflows/{workflow_id}/messages", service_url=COUNSELING_SERVICE_URL)


def get_workflow_logs(workflow_id: str) -> list[dict]:
    return _request("GET", f"/api/v1/workflows/{workflow_id}/logs", service_url=COUNSELING_SERVICE_URL).get("events", [])


def download_workflow_export(workflow_id: str) -> bytes:
    url = f"{COUNSELING_SERVICE_URL}/api/v1/workflows/{workflow_id}/export.xlsx"
    try:
        response = requests.get(url, headers=_auth_headers(), timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.exceptions.RequestException as exc:
        raise BackendError("Could not reach the EduPath-AI backend. Please try again.") from exc
    if not response.ok:
        raise _friendly_error_for_response(response)
    return response.content


# ---------------------------------------------------------------------------
# Memory -- mirrors Agent Memory Service
# ---------------------------------------------------------------------------


def list_memory(profile_id: str) -> list[dict]:
    return _request("GET", f"/api/v1/memory/{profile_id}", service_url=MEMORY_SERVICE_URL)


# ---------------------------------------------------------------------------
# SOP -- mirrors Document Studio & SOP Service
# ---------------------------------------------------------------------------


def generate_sop(profile_id: str, target_program: str | None = None, target_university: str | None = None, prompt: str | None = None) -> dict:
    return _request("POST", "/api/v1/sop/generate", json={
        "profile_id": profile_id, "target_program": target_program, "target_university": target_university, "prompt": prompt,
    }, service_url=DOCUMENT_SERVICE_URL)


def revise_sop(profile_id: str, sop_id: str, feedback: str) -> dict:
    return _request("POST", "/api/v1/sop/revise", json={"profile_id": profile_id, "sop_id": sop_id, "feedback": feedback}, service_url=DOCUMENT_SERVICE_URL)


def get_sop(sop_id: str) -> dict:
    return _request("GET", f"/api/v1/sop/{sop_id}", service_url=DOCUMENT_SERVICE_URL)


def list_sops(profile_id: str) -> list[dict]:
    return _request("GET", "/api/v1/sop", params={"profile_id": profile_id}, service_url=DOCUMENT_SERVICE_URL)


# ---------------------------------------------------------------------------
# Opportunities -- mirrors Opportunity & University Catalog Service
# ---------------------------------------------------------------------------


def list_opportunities() -> list[dict]:
    return _request("GET", "/api/v1/opportunities", service_url=CATALOG_SERVICE_URL)


@st.cache_data(ttl=15, show_spinner=False)
def list_opportunities_cached() -> list[dict]:
    return list_opportunities()


def get_opportunity(opportunity_id: str) -> dict:
    return _request("GET", f"/api/v1/opportunities/{opportunity_id}", service_url=CATALOG_SERVICE_URL)


# ---------------------------------------------------------------------------
# Applications -- mirrors Admissions Tracker Service
# ---------------------------------------------------------------------------


def list_applications(profile_id: str) -> list[dict]:
    return _request("GET", "/api/v1/applications", params={"profile_id": profile_id}, service_url=TRACKER_SERVICE_URL) or []


def create_application(payload: dict) -> dict:
    return _request("POST", "/api/v1/applications", json=payload, service_url=TRACKER_SERVICE_URL)


def get_application(application_id: str) -> dict:
    return _request("GET", f"/api/v1/applications/{application_id}", service_url=TRACKER_SERVICE_URL)


def update_application(application_id: str, payload: dict) -> dict:
    return _request("PUT", f"/api/v1/applications/{application_id}", json=payload, service_url=TRACKER_SERVICE_URL)
