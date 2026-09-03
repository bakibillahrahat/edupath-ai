# Modular Monolith & Microservices Architecture Blueprint

**EduPath AI — Domain-Driven Modular System & Microservice Roadmap**

---

## 1. Architectural Overview

EduPath AI is structured as a **Modular Architecture (Modular Monolith / Domain-Driven Design)**. Rather than organizing code by technical layers (all models in one file, all routes in another), the platform is segmented into **6 Autonomous Domain Modules (Bounded Contexts)**.

Each domain module encapsulates its own:
- **`models.py`**: Database entities owned strictly by this domain.
- **`schemas.py`**: Request / Response Data Transfer Objects (DTOs) and contracts.
- **`repository.py`**: Data access queries and persistence.
- **`service.py`**: Business logic, rules, and workflows.
- **`router.py`**: FastAPI HTTP REST endpoints for the module.

```text
                                  ┌────────────────────────┐
                                  │   Streamlit Frontend   │
                                  └───────────┬────────────┘
                                              │
                    HTTP REST Requests (Configurable Microservice URLs)
                                              │
                                              ▼
                                  ┌────────────────────────┐
                                  │   FastAPI API Gateway  │
                                  │     (app/main.py)      │
                                  └───────────┬────────────┘
         ┌──────────────────┬─────────────────┼─────────────────┬──────────────────┐
         ▼                  ▼                 ▼                 ▼                  ▼
  ┌──────────────┐   ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   ┌──────────────┐
  │   profile/   │   │   catalog/   │  │ counseling/  │  │  documents/  │   │   tracker/   │
  │   Domain     │   │   Domain     │  │   Domain     │  │   Domain     │   │   Domain     │
  │ • User/Auth  │   │ • University │  │ • 7 Agents   │  │ • Document   │   │ • Application│
  │ • SSC/HSC    │   │ • Program    │  │ • LangGraph  │  │ • RAG Vector │   │ • Milestones │
  │ • MSc for PhD│   │ • Opportunity│  │ • Sessions   │  │ • SOP Studio │   │ • Export     │
  └──────────────┘   └──────────────┘  └──────────────┘  └──────────────┘   └──────────────┘
```

---

## 2. The 6 Bounded Contexts (Future Microservices)

| Domain Module | Future Microservice Name | Responsibilities | Dedicated Port (When Extracted) |
|---|---|---|---|
| **`modules/profile`** | `edupath-profile-service` | User authentication (Google OAuth / JWT), student academic credentials (SSC, HSC, tests, GPA, degrees, ECA, MSc for PhD). | `8001` |
| **`modules/catalog`** | `edupath-catalog-service` | University catalog directory, degree programs, funding/scholarships, admission criteria, vector search & scrapers. | `8002` |
| **`modules/counseling`** | `edupath-counseling-service` | 7-Agent AI Swarm orchestration (Supervisor, Profile Analyst, University Matcher, Scholarship Engine, Strategist, Compliance, Faculty Outreach), LangGraph workflow execution, HITL decisions. | `8003` |
| **`modules/documents`** | `edupath-document-service` | SOP generation, paragraph review, student document uploads, chunking, and pgvector embeddings. | `8004` |
| **`modules/tracker`** | `edupath-tracker-service` | Application milestones, deadlines, status tracking (draft, submitted, accepted, rejected), checklist tasks, export (PDF, CSV, Notion). | `8005` |
| **`modules/memory`** | `edupath-memory-service` | Long-term student agent memory, conversational context, preference store. | `8006` |

---

## 3. How to Extract a Domain into an Independent Microservice

When you are ready to split any module into a separate microservice:

### Step 1: Copy the Domain Folder
Move `backend/app/modules/{domain}` into a new service folder (e.g. `services/{domain}-service/app/`).

### Step 2: Add a Standalone FastAPI `main.py`
Create a lightweight `main.py` for the service:
```python
from fastapi import FastAPI
from app.router import router

app = FastAPI(title="EduPath Profile Microservice")
app.include_router(router, prefix="/api/v1")
```

### Step 3: Configure Frontend Service Routing
The Streamlit frontend (`streamlit_app/utils/config.py` and `streamlit_app/api/client.py`) is already decoupled and routes via environment variables:

```bash
# In production or docker-compose:
PROFILE_SERVICE_URL=http://profile-service:8001
CATALOG_SERVICE_URL=http://catalog-service:8002
COUNSELING_SERVICE_URL=http://counseling-service:8003
DOCUMENT_SERVICE_URL=http://document-service:8004
TRACKER_SERVICE_URL=http://tracker-service:8005
MEMORY_SERVICE_URL=http://memory-service:8006
```

If an environment variable is omitted, it defaults back to `BACKEND_URL` (`http://localhost:8000`), ensuring 100% backward compatibility with the unified modular monolith.

---

## 4. Codebase Directory Map

```text
backend/app/
├── modules/                   # Autonomous Bounded Contexts
│   ├── profile/               # Identity & Student Profile Domain
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── router.py
│   ├── catalog/               # Opportunities & Universities Domain
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── router.py
│   ├── counseling/            # AI Swarm & Counseling Workflow Domain
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── router.py
│   ├── documents/             # Document Studio & SOP RAG Domain
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── router.py
│   ├── tracker/               # Admissions Lifecycle & Tracker Domain
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── repository.py
│   │   ├── service.py
│   │   └── router.py
│   └── memory/                # Agent Memory Domain
│       ├── models.py
│       ├── schemas.py
│       ├── repository.py
│       ├── service.py
│       └── router.py
├── core/                      # Shared Cross-Cutting Infrastructure
│   ├── config.py              # Application settings
│   ├── security.py            # JWT and encryption
│   ├── exceptions.py          # Error handling
│   └── logging.py             # Structured logging
├── database/                  # Shared DB Session & Migration
│   ├── base.py
│   ├── session.py
│   └── migrations/
└── main.py                    # Unified Gateway Application
```
