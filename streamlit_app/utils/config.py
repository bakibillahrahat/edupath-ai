from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load streamlit_app/.env regardless of the process's current working directory.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
# Microservice routing endpoints (defaults to unified backend for modular monolith)
PROFILE_SERVICE_URL = os.getenv("PROFILE_SERVICE_URL", BACKEND_URL).rstrip("/")
CATALOG_SERVICE_URL = os.getenv("CATALOG_SERVICE_URL", BACKEND_URL).rstrip("/")
COUNSELING_SERVICE_URL = os.getenv("COUNSELING_SERVICE_URL", BACKEND_URL).rstrip("/")
DOCUMENT_SERVICE_URL = os.getenv("DOCUMENT_SERVICE_URL", BACKEND_URL).rstrip("/")
TRACKER_SERVICE_URL = os.getenv("TRACKER_SERVICE_URL", BACKEND_URL).rstrip("/")
MEMORY_SERVICE_URL = os.getenv("MEMORY_SERVICE_URL", BACKEND_URL).rstrip("/")

REQUEST_TIMEOUT_SECONDS = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "30"))
# The opportunity_discovery workflow runs several sequential agent calls
# synchronously on the backend, so it needs a generous client timeout.
WORKFLOW_TIMEOUT_SECONDS = float(os.getenv("WORKFLOW_TIMEOUT_SECONDS", "600"))
