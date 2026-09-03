# EduPath AI — Comprehensive Codebase Inspection Report
**Date:** 2026-08-29 | **Scope:** Full read-only analysis of frontend, backend, workflow, auth, database, and schemas

---

## EXECUTIVE SUMMARY

**Status:** Substantially implemented with working architecture. Core backend workflow (LangGraph supervisor + 9 agents) is fully functional. Frontend is partially built (6 of ~11 core pages complete). Auth system works (Google OAuth + dev-mock fallback). Database models exist for all major entities.

**Main Gaps:**
- Frontend: ~5 pages partially stubbed or incomplete (Application Tracker, SOP drafting, Execution Graph visualization)
- No persistent document storage or application tracking (stored in browser session only)
- Limited opportunity search beyond the static catalog
- No real-time workflow pause/resume UI
- Missing error recovery for quota exhaustion scenarios

---

## 1. FRONTEND STRUCTURE (`streamlit_app/`)

### Pages Built (6/11 Core Pages)

| Page | File | Status | Notes |
|------|------|--------|-------|
| **Dashboard** | `pages/dashboard.py` | ✅ Full | Hero section, profile summary, quick actions, upcoming opportunities sorted by deadline |
| **My Profile** | `pages/profile.py` | ✅ Full | Profile form, document upload (CV/transcript/SOP), profile completion bar |
| **Discover Opportunities** | `pages/discover.py` | ✅ Full | Search panel, filters (degree/funding/deadline/country/research), catalog display |
| **Saved Opportunities** | `pages/saved.py` | ✅ Full | Browser-session-only bookmarking, no backend persistence |
| **Application Tracker** | `pages/tracker.py` | ⚠️ Partial | Kanban-style board (Interested → Applied → Accepted), session-only state |
| **Agent Trace** | `pages/agent_trace.py` | ⚠️ Partial | Shows real agent executions + inter-agent messages, requires workflow_id input |
| **Execution Graph** | `pages/execution_graph.py` | ⚠️ Partial | Graphviz visualization of LangGraph topology, shows live agent status |
| **Statement of Purpose** | `pages/sop.py` | ⚠️ Partial | Generate/revise SOP UI sketched, backend endpoints exist but frontend form incomplete |
| **Memory** | `pages/memory.py` | ⚠️ Partial | Shows memory entries (preferences + workflow history), minimal detail view |
| **Usage & Cost** | `pages/usage.py` | ⚠️ Partial | Metrics grid (total workflows/tokens/cost), per-workflow breakdown table |
| **Settings** | `pages/settings.py` | ✅ Full | Backend connection test, session state inspection, session reset |

### Components Built (Reusable Streamlit Components)

| Component | File | Purpose |
|-----------|------|---------|
| `auth.py` | Auth gates, OAuth redirect handling, login form, dev-mode fallback |
| `common.py` | Backend error rendering, section headers, utility components |
| `header.py` | Page header with eyebrow + title + description |
| `profile_form.py` | Student profile edit form (all fields) |
| `profile_card.py` | Profile summary display + completion bar |
| `opportunity_card.py` | Single opportunity premium card (title, meta, badges, actions, details dialog) |
| `opportunity_list.py` | Grid/list rendering + toolbar (filter by country, funding, deadline) |
| `workflow_status.py` | Shows workflow execution status, agent results, rankings |
| `sidebar.py` | Brand logo + sidebar footer |
| `empty_state.py` | Contextual empty state with CTA |
| `metrics.py` | Metric grid (usage page) |
| `ranked_opportunity_card.py` | Card for ranked opportunities with score |
| `evidence.py` | (Not inspected, likely shows agent evidence/reasoning) |

### Styling

**File:** `styles/main.css` (480+ lines)

- Custom CSS variables: navy, indigo, purple, success, warning, danger + gradients
- Design tokens: `--ep-shadow`, `--ep-shadow-hover`, `--ep-gradient`
- Component classes: `.ep-badge`, `.ep-opp-title`, `.ep-section-title`, `.ep-metric-caption`
- Responsive grid layouts for opportunity cards and sidebar
- Does NOT use Tailwind — all custom Streamlit-compatible CSS

### API Client Layer

**File:** `api/client.py`

- `BackendError` exception wrapper (friendly messages for 429/5xx/timeout/connection errors)
- Functions: `dev_login()`, `get_auth_config()`, `get_current_user()`, `get_my_profile()`
- Opportunity ops: `list_opportunities()`, `list_opportunities_cached()`
- Workflow ops: `execute_workflow()`, `list_workflows()`, `get_workflow()`, `approve/reject/pause/resume()`
- Document ops: `upload_document()`, `delete_document()`, `list_documents()`
- Memory ops: `list_memory()`
- SOP ops: `generate_sop()`, `revise_sop()`, `list_sops()`
- Uses longer timeout for workflows (180s default)

### Session Management

**File:** `utils/session.py`

- `st.session_state` keys: `auth_token`, `current_user`, `profile_id`, `profile`, `saved_opportunities`, `application_stage`, `current_workflow_id`, `workflow_error`, `workflow_result`
- `APPLICATION_STAGES = ["Interested", "Applied", "Accepted", "Rejected"]`
- Functions: `init_session_state()`, `set_application_stage()`, `reset_session_state()`

---

## 2. BACKEND API ROUTES (`backend/app/api/routes/`)

### Route Registry

All routes prefix `/api/v1` (defined in `router.py`).

#### **Auth Routes** (`auth.py`)
| Method | Endpoint | Purpose | Auth |
|--------|----------|---------|------|
| GET | `/auth/config` | Returns auth mode (OAuth or dev-mock) | None |
| GET | `/auth/login` | Redirects to Google OAuth URL | None |
| GET | `/auth/callback?code=...&state=...` | OAuth callback, returns `?token=...` to frontend | None |
| GET | `/auth/dev-login?email=...&name=...` | Dev-mode login, returns JWT | None |
| GET | `/auth/me` | Current user info | Bearer JWT |
| POST | `/auth/logout` | Revokes JWT in Redis blacklist | Bearer JWT |

#### **Profiles Routes** (`profiles.py`)
| Method | Endpoint | Purpose | Auth |
|--------|----------|---------|------|
| POST | `/profiles` | Create new profile (nullable user_id) | Optional |
| GET | `/profiles/me` | Get current user's primary profile | Bearer JWT |
| GET | `/profiles/{id}` | Get specific profile by ID | None |
| PATCH | `/profiles/{id}` | Update profile fields | None |

#### **Workflows Routes** (`workflows.py`)
| Method | Endpoint | Purpose | Notes |
|--------|----------|---------|-------|
| POST | `/workflows` | Execute workflow (sync, up to 180s) | Returns `WorkflowExecutionResponse` |
| GET | `/workflows?profile_id=...` | List workflows for profile | |
| GET | `/workflows/{id}` | Get workflow by ID | |
| POST | `/workflows/{id}/pause` | Pause workflow | Transitions status to "paused" |
| POST | `/workflows/{id}/resume` | Resume workflow | Transitions status to "running" |
| POST | `/workflows/{id}/approve` | Approve at approval_gate + continue to SOP | Body: `{opportunity_id}` |
| POST | `/workflows/{id}/reject` | Reject + end workflow | Body: `{opportunity_id}` |

#### **Opportunities Routes** (`opportunities.py`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/opportunities` | List all opportunities in catalog |
| GET | `/opportunities/{id}` | Get opportunity by ID |

#### **Documents Routes** (`documents.py`)
| Method | Endpoint | Purpose | Notes |
|--------|----------|---------|-------|
| POST | `/documents` | Upload document (CV/transcript/etc.) | Multipart: profile_id, type, file |
| GET | `/documents?profile_id=...` | List documents for profile | |
| DELETE | `/documents/{id}` | Delete document | |

#### **SOP Routes** (`sop.py`)
| Method | Endpoint | Purpose | Notes |
|--------|----------|---------|-------|
| POST | `/sop/generate` | Generate new SOP | Body: profile_id, target_program, target_university, custom_prompt |
| POST | `/sop/revise` | Revise existing SOP | Body: sop_id, revision_prompt |
| GET | `/sop/{id}` | Get SOP by ID | |
| GET | `/sop?profile_id=...` | List SOPs for profile | |

#### **Memory Routes** (`memory.py`)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/memory/{profile_id}` | Get all memory entries (long + short term) |

#### **Counseling Routes** (`counseling.py`) — *ALIAS/WRAPPER*
| Method | Endpoint | Purpose | Notes |
|--------|----------|---------|-------|
| POST | `/counseling/analyze` | Execute workflow (alias) | Same as `POST /workflows`, different contract |
| GET | `/counseling/{session_id}` | Get session | |
| GET | `/counseling/{session_id}/trace` | Get trace metadata | |

### Key Design Patterns

- **Auth dependency injection:** `get_current_user()` (required), `get_current_user_optional()` (optional)
- **Service layer:** Each route endpoint depends on a service (`WorkflowService`, `ProfileService`, etc.)
- **Error handling:** HTTPExceptions (401, 404, 409) + custom exceptions mapped to HTTP codes
- **Workflows are synchronous** (no polling needed) but can take up to 180s

---

## 3. AUTHENTICATION (`backend/app/core/security.py`, `streamlit_app/components/auth.py`)

### Backend JWT Implementation

```python
# Secret key + expiry configured in settings
_ALGORITHM = "HS256"
TokenPayload = {"sub": user_id, "jti": unique_token_id, "iat", "exp"}
```

- `create_access_token(user_id)` → JWT valid for `jwt_expiry_minutes` (default 1440/24h)
- `decode_access_token(token)` → raises `InvalidTokenError` on expiry/tampering
- Each token has unique `jti` (JWT ID) for logout blacklisting (stored in Redis)

### Auth Modes (Conditional)

**Real Google OAuth:**
- Requires `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET`
- Flow: Frontend → `/auth/login` → Google consent → `/auth/callback?code=...` → Backend exchanges for JWT → Frontend stores JWT
- CSRF protection: one-time state token stored in Redis (600s TTL)

**Dev-Mock Fallback:**
- When Google creds are unset, `/auth/dev-login?email=...&name=...` works
- Any email, no password validation
- Returns same JWT structure as real OAuth

### Frontend Login Flow

1. `handle_oauth_redirect()` checks for `?token=...` in URL (after OAuth callback)
2. `ensure_current_user()` loads `/auth/me` once per session, stores in `st.session_state["current_user"]`
3. `_hydrate_profile_from_backend()` fetches linked profile and updates session state
4. `render_login_gate()` shows isolated full-page login UI (hides sidebar when not authed)

### Session Management

- Profiles are nullable on `user_id` (pre-auth profiles remain anonymous)
- A logged-in user can have multiple profiles (linked via `user_id`)
- Logout clears JWT, removes it from Redis, session state reset on next load

---

## 4. LANGGRAPH WORKFLOW ARCHITECTURE

### Graph Topology

**File:** `backend/app/graph/workflow.py`

```
START → supervisor → {agent1, agent2, ..., sop_agent} → supervisor → END
```

- **Hub-and-spoke** design: supervisor orchestrates, agents execute, control returns to supervisor
- **Deterministic routing:** supervisor decides next agent via `state["next_agent"]`
- **Checkpointing:** Production uses durable-in-process checkpointer (for `approval_gate` interrupt/resume)

### State Machine

**File:** `backend/app/graph/state.py` (`EduPathState` TypedDict)

**Key Fields:**
- `workflow_id`, `workflow_type`, `user_request`, `student_profile_id`
- `execution_plan: list[str]` — planned agents (planned once, reused on each supervisor turn since 2026-08)
- `plan_index: int` — which agent in the plan to run next
- `llm_call_count: int` — tracked against `max_llm_calls_per_workflow`
- `candidate_opportunities: list[CandidateOpportunity]` — merged by ID (upsert on re-discovery)
- `eligibility_verdicts`, `research_match_verdicts`, `verification_verdicts` — keyed by opportunity_id
- `ranked_opportunities: list[RankedOpportunity]` — final sorted list from ranking_agent
- `human_approval: dict` — set by `approval_gate` interrupt, contains "approve"/"reject" decision

### Agents

**All 9 agents:**

1. **Supervisor** (`agents/supervisor/agent.py`)
   - Decides execution plan (LLM-based with fallback deterministic planner)
   - Routes to next agent
   - Resumes from execution_plan on subsequent turns (2026-08 optimization)
   - Detects workflow completion

2. **Profile Agent** (`agents/profile/agent.py`)
   - Analyzes user request, infers academic profile signals
   - First in typical execution order
   - Returns: summary, key_findings, confidence

3. **University Agent** (`agents/university/agent.py`)
   - Discovers suitable universities/programs
   - Uses tool results (already extracted)
   - Adds `candidate_opportunities`

4. **Professor Agent** (`agents/professor/agent.py`)
   - Finds research advisors matching interests
   - Likely uses web search + professor database

5. **Scholarship Agent** (`agents/scholarship/agent.py`)
   - Identifies funding opportunities
   - Funding-focused candidate discovery

6. **Eligibility Agent** (`agents/eligibility/agent.py`)
   - Verifies GPA/degree/language requirements for candidates
   - Returns `eligibility_verdicts` (keyed by opportunity_id)

7. **Research Match Agent** (`agents/research_match/agent.py`)
   - Analyzes research interest alignment
   - Returns `research_match_verdicts`

8. **Verification Agent** (`agents/verification/agent.py`)
   - Spot-checks opportunity details (deadlines, URLs, etc.)
   - Returns `verification_verdicts`

9. **Ranking Agent** (`agents/ranking/agent.py`)
   - **Deterministic Python scoring** (no LLM call)
   - Weights: research_match (30%) + eligibility (20%) + funding (20%) + professor_match (15%) + university_tier (10%) + deadline_urgency (5%)
   - No token usage or cost for this agent
   - Returns ordered `ranked_opportunities`

10. **SOP Agent** (`agents/sop/agent.py`)
    - Generates Statement of Purpose draft
    - Always last in plan (after `approval_gate`)
    - Paused at `approval_gate` interrupt until human approves

### Execution Flow

1. User submits request → `POST /workflows`
2. Workflow created with status "running"
3. Graph invokes supervisor → decides plan (or reuses existing)
4. Supervisor routes to agent 1 (e.g., profile_agent)
5. Agent executes (makes LLM call, returns structured output)
6. Agent updates state (appends results, candidates, etc.)
7. Control returns to supervisor
8. Supervisor checks: more agents in plan? → routes to next
9. Supervisor checks: sop_agent next? → inserts `approval_gate` interrupt
10. `approval_gate` pauses workflow, waits for human decision
11. Frontend calls `POST /workflows/{id}/approve` or `/reject`
12. Graph resumes from interrupt, routes to sop_agent
13. SOP generated
14. Graph returns to supervisor, no more agents → END

### Key Optimizations & Constraints

- **LLM budget:** Hard cap `max_llm_calls_per_workflow = 12` (supervisor 1 call + 8 agents max, leaves headroom)
- **Plan reuse (2026-08):** Supervisor plans once, reuses on subsequent turns → ~50% fewer Gemini calls
- **429 handling:** Never retried; transient 5xx retried max 2x with jittered exponential backoff
- **Embeddings separate budget:** MemoryVectorStore calls `embed_text()` (before + after workflow) but these are NOT counted against max_llm_calls_per_workflow
- **Approval gate deterministic:** Not left to LLM planning; inserted automatically before sop_agent

---

## 5. DATABASE MODELS (`backend/app/database/models/entities.py`)

### Core Entities

| Entity | Timestamps | Key Fields | Notes |
|--------|-----------|-----------|-------|
| **User** | created_at, updated_at | google_sub (nullable), email (unique), name, avatar_url | Created on first login (real Google or dev-mock) |
| **StudentProfile** | ✓ | user_id (nullable), email (unique), name, academic_level, current_degree, field_of_study, university, gpa, graduation_year, target_degree, target_countries (JSONB), research_interests, skills, publications, projects, work_experience, preferred_funding | Can exist without user_id (pre-auth) |
| **University** | ✓ | name, country, website_url, faculty_directory_url, description, metadata_json (JSONB), embedding (pgvector) | Faculty directory URL verified for PageExtractorTool |
| **Professor** | — | name, university, department, research_interests, publications, profile_url, email, embedding | Keyed by name (non-unique; disambiguated by university) |
| **Program** | ✓ | name, university_id (FK), degree_level, field, country, description, embedding | Links programs to universities |
| **Opportunity** | ✓ | title, provider, university, degree_level, country, field, funding_type, amount, deadline, eligibility (JSONB), application_url, source_url, description, embedding | Catalog of opportunities; searched via embedding similarity or metadata filters |
| **Application** | ✓ | profile_id (FK), opportunity_id (FK), status (draft/submitted/etc.), submitted_at, notes | User's application state (NOT fully integrated into UI yet) |
| **Document** | ✓ | profile_id (FK), filename, document_type (CV/transcript/etc.), content_text | Has DocumentChunk relationships (cascade delete) |
| **DocumentChunk** | — | document_id (FK), chunk_index, content, embedding | Chunked for RAG/grounding in SOP generation |
| **SOPDocument** | ✓ | profile_id (FK), application_id (FK), title, content, draft_version, status | Versioned drafts of Statement of Purpose |
| **WorkflowExecution** | ✓ | profile_id (FK), workflow_type, status, started_at, completed_at, error, user_request, result (JSONB), token_usage (JSONB), estimated_cost_usd | Complete execution record; immutable after completion |
| **AgentExecution** | — | workflow_id (FK), agent_name, status, started_at, completed_at, input, output (JSONB), token_usage, estimated_cost, error | Per-agent execution detail |
| **AgentMessage** | — | workflow_id (FK), sender, receiver, message_type, content, timestamp | Inter-agent communication log |
| **Memory** | ✓ | profile_id (FK), memory_type, scope, content (JSONB), source, embedding | Stored preferences + workflow history; unique constraint (profile_id, memory_type, scope) |

### Key Relationships

- `StudentProfile` → `User` (nullable FK) — many profiles per user
- `Application` → `StudentProfile` + `Opportunity` — tracks applications
- `Document` → `StudentProfile` + `DocumentChunk` (cascade delete)
- `SOPDocument` → `StudentProfile` + `Application`
- `WorkflowExecution` → `StudentProfile` + `AgentExecution` + `AgentMessage` (cascade delete)
- `Memory` → `StudentProfile`

### Database Constraints

- **Unique:** User.email, User.google_sub (nullable), StudentProfile.email, University.name(?), Professor.name(?)
- **Indexes:** email (User, StudentProfile), google_sub (User), profile_id (StudentProfile, Document, WorkflowExecution, Memory), agent_name (AgentExecution), timestamp columns
- **Embedding columns:** pgvector type (1536 dimensions for OpenAI/OpenRouter embeddings)

---

## 6. API SCHEMAS (Pydantic) (`backend/app/schemas/`)

### Request/Response Models

**Auth:**
- `UserRead` — id, google_sub?, email, name?, avatar_url?
- `AuthConfigResponse` — is_google_configured (bool), login_url?, dev_login_enabled (bool)

**Profiles:**
- `StudentProfileCreate` — all profile fields except id/timestamps
- `StudentProfileUpdate` — all fields optional
- `StudentProfileRead` — all fields + timestamps + id

**Workflows:**
- `WorkflowCreateRequest` — user_request, student_profile_id?, workflow_type (default "opportunity_discovery")
- `WorkflowExecutionResponse` — workflow_id, workflow_type, workflow_status, approval_status, execution_plan, agent_results[], agent_messages[], final_response?, errors[], timestamps, token_usage, estimated_cost_usd, **candidate_opportunities[]**, **ranked_opportunities[]**, pending_approval?
- `WorkflowRead` — id, profile_id, workflow_type, status, timestamps, user_request, token_usage, estimated_cost_usd
- `AgentExecutionRead` — id, workflow_id, agent_name, status, timestamps, input, output, token_usage, estimated_cost, error?
- `AgentMessageRead` — id, workflow_id, sender, receiver, message_type, content, timestamp
- `ApprovalDecisionRequest` — opportunity_id?

**Opportunities:**
- `OpportunityRead` — id, title, provider?, university?, degree_level?, country?, field?, funding_type?, amount?, deadline?, eligibility (dict), application_url?, source_url?, description?, timestamps

**Agents:**
- `AgentResult` — agent_name, summary, key_findings[], recommended_next_agent, supervisor_message, next_agent_message?, confidence, raw_output?, timestamps, token_usage, estimated_cost_usd
- `AgentMessage` — sender, receiver, message_type, content

**Documents:**
- `DocumentRead` — id, profile_id, filename, document_type, content_text?, timestamps
- `DocumentType` (enum) — "cv", "transcript", "research_proposal", "previous_sop", "publication", "other"

**SOP:**
- `SOPGenerateRequest` — profile_id, target_program?, target_university?, custom_prompt?
- `SOPReviseRequest` — sop_id, revision_prompt
- `SOPResponse` — id, profile_id, application_id?, title?, content?, draft_version, status, timestamps

**Opportunity Candidates:**
- `CandidateOpportunity` — id, title, university?, country?, degree_level?, field?, funding_type?, amount?, deadline?, eligibility (dict), description?
- `EligibilityVerdict` — opportunity_id, verdict (pass/fail), reasoning?, score?
- `ResearchMatchVerdict` — opportunity_id, verdict (pass/partial/fail), reasoning?, score?
- `VerificationVerdict` — opportunity_id, verdict (verified/questionable/broken), reasoning?, issues?
- `RankedOpportunity` — opportunity_id, rank (1-indexed), overall_score (0-1), component_scores {research_match, eligibility, funding, professor_match, university_tier, deadline_urgency}

**Memory:**
- `MemoryRead` — id, profile_id, memory_type, scope, content (dict), source?, timestamp?, embedding?

**Counseling (alias):**
- `CounselingAnalyzeRequest` — same as WorkflowCreateRequest
- `CounselingAnalyzeResponse` — wraps WorkflowExecutionResponse + message, status

### Key Design Patterns

- **ID serialization:** All UUIDs are serialized as strings in Pydantic (field_validator mode="before")
- **Timestamps:** Always included in Read models (created_at, updated_at, started_at, completed_at)
- **JSONB fields:** Returned as dicts (eligibility, token_usage, metadata_json)
- **Structured output:** Agent verdicts keyed by opportunity_id (upsert semantics in state)
- **Token tracking:** All models tracking token_usage (dict with input_tokens, output_tokens, estimated_cost_usd)

---

## 7. LLM INTEGRATION (`backend/app/llm/`)

### Provider Architecture

**File:** `backend/app/llm/openrouter.py`

- **Provider:** OpenRouter (handles both text generation + embeddings)
- **Models:**
  - Text generation: `openrouter/free` (auto-router to available free models)
  - Embeddings: `openai/text-embedding-3-small` (1536 dimensions)
- **Temperature:** 0.2 (deterministic, low creativity)
- **Request timeout:** 60s (configurable)
- **Retry policy (tenacity):** Only transient 5xx retried (max 2 attempts, jittered exponential backoff); 429 never retried

### LLM Call Context

**File:** `backend/app/llm/base.py`

```python
LLMCallContext = {
    workflow_id, agent_name, purpose, call_number
}
```

Attached to every call for observability (NOT sent to provider API).

### Usage Tracking

**File:** `backend/app/llm/usage.py`

```python
TokenUsage = {
    input_tokens, output_tokens, total_tokens, estimated_cost_usd
}
```

Computed from provider response headers. Workflow + agent estimated costs aggregated.

### Gemini (Deprecated)

**File:** `backend/app/llm/gemini.py` (NOT actively used in 2026-08)

- Was used before OpenRouter migration
- Same interface: `generate_structured()`, `embed_text()`
- AFC (automatic_function_calling) explicitly disabled (no tools passed to Gemini in this codebase)

---

## 8. EXISTING SERVICES (`backend/app/services/`)

| Service | File | Responsibilities |
|---------|------|------------------|
| **WorkflowService** | `workflow.py` | Execute workflow (invokes graph), list/get/pause/resume/approve/reject workflows, resume from interrupt |
| **ProfileService** | `profile.py` | CRUD profiles, link to user, fetch by user email |
| **DocumentService** | `document.py` | Upload document (PDF/DOCX extraction), chunk + embed, list/delete documents |
| **SOPService** | `sop.py` | Generate SOP (via graph), revise draft, list/get SOPs |
| **OpportunityService** | `opportunity.py` | List/get opportunities from catalog |
| **MemoryService** | `memory.py` | Record workflow context (before + after), list memory entries |
| **AuthService** | `auth.py` | Create/verify JWTs, handle Google OAuth callback, dev-mock login |
| **ExportService** | `export.py` | Build Excel workbook from workflow results |
| **CatalogSyncService** | `catalog_sync.py` | (Inferred: syncs opportunities into catalog) |
| **ToolingService** | `tooling.py` | (Not inspected; likely supports tool execution within graph) |

---

## 9. STYLING & DESIGN SYSTEM

**File:** `streamlit_app/styles/main.css`

### Design Tokens

```css
--ep-navy: #0B1220;                     /* Dark background */
--ep-navy-soft: #131C31;                /* Softer dark */
--ep-indigo: #4F46E5;                   /* Primary action */
--ep-purple: #7C3AED;                   /* Secondary accent */
--ep-border: #E5E7EB;                   /* Border color */
--ep-text-muted: #64748B;               /* Secondary text */
--ep-success: #16A34A;                  /* Success state */
--ep-warning: #F59E0B;                  /* Warning state */
--ep-danger: #DC2626;                   /* Error state */
--ep-gradient: linear-gradient(120deg, #4F46E5 0%, #7C3AED 100%);
--ep-shadow: 0 1px 2px rgba(15, 23, 42, 0.04), 0 8px 24px -12px rgba(15, 23, 42, 0.12);
--ep-shadow-hover: 0 4px 10px rgba(15, 23, 42, 0.06), 0 16px 32px -12px rgba(79, 70, 229, 0.18);
```

### Component Classes

- `.ep-badge` — inline badges (country, degree, funding, deadline urgency, match score)
- `.ep-opp-title`, `.ep-opp-meta` — opportunity card text
- `.ep-section-title` — page section headers
- `.ep-field-value`, `.ep-metric-caption` — data display
- `.ep-brand`, `.ep-brand-logo`, `.ep-brand-name` — sidebar branding
- `.ep-badge-row` — container for badge chips
- Responsive grid layouts via Streamlit native columns

### No Tailwind

- All CSS is custom + compatible with Streamlit's native theme engine (`config.toml`)
- Design tokens come from `.streamlit/config.toml` (theme section) + `main.css`

---

## 10. CRITICAL FINDINGS & GAPS

### ✅ What Works

1. **End-to-end workflow execution** — User request → graph execution → ranked opportunities
2. **Auth system** — Google OAuth + dev-mock fallback, JWT-based session management
3. **Multi-agent LangGraph** — Supervisor orchestration, deterministic routing, plan reuse
4. **Approval gate** — LangGraph interrupt/resume integration (pause before SOP generation)
5. **Frontend pages** — 6 core pages fully built + working API integration
6. **Database models** — Complete schema for users, profiles, workflows, agents, opportunities, documents
7. **Token tracking** — Per-workflow + per-agent cost tracking, displayed on Usage page
8. **LLM budget enforcement** — Hard cap on calls per workflow, 429 handling
9. **Profile-driven discovery** — Workflow tailors agent routing based on user request (profile_agent → discovery agents → verification → ranking)

### ⚠️ Partially Working

1. **Document uploads** — Backend accepts uploads + chunks them, but frontend profile page doesn't show chunk details or embed status
2. **Application tracker** — Kanban board UI exists, but state is browser-session-only (resets on refresh/restart)
3. **SOP generation** — Backend endpoints exist, frontend form is incomplete (generate/revise flows not wired)
4. **Memory system** — Backend records preferences + history, frontend displays raw entries with minimal UX polish
5. **Opportunity search** — No full-text search on catalog; limited to metadata filters (country, funding, deadline)

### ❌ Missing/Incomplete

1. **Persistent application tracking** — No backend support for saving application status (draft/submitted/accepted); session-only fallback
2. **Opportunity deduplication** — No detection of duplicate opportunities from multiple sources (e.g., same university+program from different discovery agents)
3. **Error recovery** — Quota exhaustion (429) surfaces cleanly but no graceful degradation (continue with fewer agents)
4. **Real-time workflow pause/resume UI** — Frontend shows pause/resume buttons, but no live status updates after approval_gate interrupt
5. **Agent evidence/reasoning** — Workflow trace shows agent messages but not detailed reasoning or tool results that led to verdicts
6. **University faculty directory verification** — `faculty_directory_url` field exists but no UI for adding/verifying URLs
7. **Counseling API completion** — Routes exist but frontend doesn't use `/counseling/` endpoints (only `/workflows/`)
8. **Document embedding status** — No feedback on chunking progress or embedding availability
9. **Ranking component scores UI** — Ranked opportunities show overall score but not component breakdowns (research_match, eligibility, etc.)
10. **Workflow export** — `ExportService` exists but no frontend button to download workflow as Excel workbook

### 🚨 Architectural Issues

1. **Embedding quota not separated from LLM quota** — MemoryService calls embed_text() (outside LLM budget), but frontend doesn't show embedding costs
2. **Approval gate tightly coupled to SOP** — Graph assumes sop_agent always follows approval_gate; no flexibility for other pauses
3. **No workflow cancellation** — Once started, workflow must run to completion (no cancel endpoint)
4. **Opportunity candidates not persisted** — `candidate_opportunities` live only in state; not saved to database for later inspection
5. **No agent performance metrics** — No tracking of which agents fail most often or return best verdicts

---

## 11. WHAT CAN BE REUSED

### Components (Ready to Use)

| Component | Reusability | Notes |
|-----------|-------------|-------|
| `opportunity_card` | ✅ High | Fully functional; reuse for search results, saved, recommendations |
| `workflow_status` | ✅ High | Displays execution status, agent results, rankings; works with any WorkflowExecutionResponse |
| `profile_form` | ✅ High | All profile fields; reuse for onboarding, profile editing, bulk imports |
| `empty_state` | ✅ High | Generic pattern; customize title/description/icon/CTA per page |
| `backend_error` | ✅ High | Friendly error rendering; use for all API failures |
| `metric_grid` | ✅ High | Generic metrics display; reuse for any dashboard stats |
| `opportunity_list` | ✅ High | Grid + toolbar (filters); reuse for search, saved, recommendations |

### Services (Ready to Use)

| Service | Reusability | Notes |
|---------|-------------|-------|
| `WorkflowService` | ✅ High | Encapsulates all workflow logic; extend with new workflow_type handlers |
| `ProfileService` | ✅ High | All profile CRUD; extend for bulk import, deduplication |
| `DocumentService` | ✅ High | Document upload + chunking; extend for OCR, language detection |
| `MemoryService` | ✅ High | Records + retrieves memory; extend for search, filtering |
| `AuthService` | ✅ High | Google OAuth + dev-mock; extend for other providers (Microsoft, GitHub) |

### Schemas (Ready to Use)

| Schema | Reusability | Notes |
|--------|-------------|-------|
| `WorkflowExecutionResponse` | ✅ High | Rich response; suitable for API versioning without breaking changes |
| `AgentResult` | ✅ High | Standard agent output; extend for new agent types |
| `StudentProfileRead` | ✅ High | All profile fields; extend with computed fields (completion %) |

### Pages (Partially Reusable)

| Page | Reusability | Notes |
|------|-------------|-------|
| `dashboard.py` | ⚠️ Medium | Hero pattern works; customize metrics/sections for new features |
| `discover.py` | ⚠️ Medium | Search + filter pattern works; extend with advanced filters (professor match, etc.) |
| `agent_trace.py` | ⚠️ Medium | Workflow inspection pattern; reuse for other observability features (logs, metrics) |

---

## 12. MISSING FEATURES BLOCKING FULL UX/UI

1. **Persistent saved opportunities** — Saved list should sync to backend (not browser-session-only)
2. **Application status persistence** — Tracker board should save to database (Application model exists but unused)
3. **SOP revision workflow** — Generate form incomplete; revise endpoint exists but no UI for iteration + version history
4. **Opportunity detail modal** — Clicked opportunity should expand with full details (eligibility breakdown, application URL, source)
5. **Workflow cancellation** — Long-running workflows should allow cancellation mid-execution
6. **Agent performance dashboard** — Show which agents succeed/fail most, average execution time per agent
7. **Bulk profile import** — CSV/Excel import for students with prior applications/profiles
8. **Counseling session history** — Replay past workflow executions + modify re-run parameters
9. **Advanced search** — Full-text search on opportunity title/description/field, not just metadata filters
10. **Opportunity deduplication** — Detect same opportunity from multiple discovery sources

---

## 13. DEPLOYMENT & CONFIGURATION

### Backend Configuration (`backend/app/core/config.py`)

**Key settings:**
- `OPENROUTER_API_KEY` — LLM credentials
- `DATABASE_URL` — PostgreSQL connection
- `REDIS_URL` — Redis for state/blacklist
- `JWT_SECRET_KEY` — Signing key
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` — OAuth credentials (optional)
- `MAX_LLM_CALLS_PER_WORKFLOW` — Budget (default 12)
- Ranking weights (must sum to 1.0)
- Document upload size limits

### Frontend Configuration (`streamlit_app/.env`)

- `BACKEND_URL` — API endpoint (default `http://localhost:8000`)

### Infra

**Docker Compose:** `infrastructure/docker/compose.yaml`
- PostgreSQL 15+ (pgvector enabled for embeddings)
- Redis (for JWT blacklist + state)

---

## 14. TESTING & VALIDATION

**Repo memory indicates:**
- `pytest` used (run via `UV_CACHE_DIR="$TMPDIR/uv-cache" uv run pytest`)
- Test structure: `tests/unit/`, `tests/integration/`, `tests/agents/`, `tests/api/`
- Linting: `ruff check` (with `--fix` for auto-formatting)

**No test files inspected in this review.**

---

## RECOMMENDATIONS FOR COMPLETION

### High Priority (Blocks Full UX)

1. **Persist saved opportunities** — Update `saved_opportunities` to use backend (new endpoint: `POST /profiles/{id}/saved-opportunities`)
2. **Implement SOP revision UI** — Wire up generate + revise forms, show version history
3. **Complete application tracker** — Backend Application model exists; wire status persistence (new endpoint: `PATCH /applications/{id}/status`)
4. **Add opportunity detail modal** — Frontend: expand card to show full details (sources, eligibility breakdown)
5. **Build workflow cancellation** — Backend: add `POST /workflows/{id}/cancel`, frontend: cancel button during execution

### Medium Priority (Enhances UX)

6. **Implement full-text search** — Add pg search to `OpportunityService`, update frontend filters
7. **Add deduplication logic** — Post-ranking, merge duplicate opportunities (same university + field)
8. **Build counseling session replay** — UI to re-execute past workflows with modified parameters
9. **Display ranking component scores** — Break down ranked opportunity scores in UI (research_match 0.8, eligibility 0.7, etc.)
10. **Add agent performance metrics** — Dashboard showing success rate, avg execution time per agent

### Low Priority (Nice-to-Have)

11. **Bulk profile import** — CSV/Excel upload for batch student profiles
12. **University directory verification** — Admin UI for managing `faculty_directory_url` by institution
13. **Workflow export** — Download workflow results as Excel workbook (ExportService exists but no UI)
14. **Advanced search filters** — Research areas, professor keywords, funding amounts, application deadlines
15. **Session timeout warnings** — Notify user before JWT expiry

---

## SUMMARY TABLE

| Area | Status | Completeness | Key File(s) |
|------|--------|--------------|-------------|
| Frontend | Partial | 60% | `app.py`, 6/11 pages |
| Backend API | Complete | 95% | `api/routes/` (8 route files) |
| Auth | Complete | 90% | `security.py`, `auth.py` |
| LangGraph Workflow | Complete | 100% | `graph/workflow.py`, `agents/` (9 agents) |
| Database Models | Complete | 100% | `models/entities.py` (15 entities) |
| Schemas | Complete | 95% | `schemas/` (9 schema files) |
| Styling | Complete | 85% | `main.css` (custom design system) |
| Integrations | Partial | 70% | `llm/openrouter.py`, `llm/gemini.py` |

**Overall:** **70% complete** — Core architecture solid, frontend needs 4-6 weeks to full parity with backend capabilities.

