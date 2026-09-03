"""
Dashboard — Student Personal Command Center & Step-by-Step Admissions Journey.
Guides applicants stage-by-stage from onboarding to university admission.
"""
from __future__ import annotations

import streamlit as st

from api.client import BackendError, get_counseling_session, list_opportunities_cached, list_workflows
from components.common import render_html, section_header
from components.empty_state import render_empty_state
from components.header import render_page_header
from utils.formatting import days_until, greeting_for_now, profile_completion
from utils.profile_guard import is_profile_complete


def _html(content: str) -> None:
    render_html(content)


def _load_catalog() -> tuple[list[dict], bool]:
    try:
        return list_opportunities_cached(), False
    except BackendError:
        return [], True


def _load_workflows(profile_id: str | None) -> list[dict]:
    if not profile_id:
        return []
    try:
        return list_workflows(profile_id)
    except BackendError:
        return []


def _hydrate_latest_session(workflows: list[dict]) -> dict | None:
    latest_result = st.session_state.get("workflow_result") or st.session_state.get("counseling_result")
    if latest_result and (latest_result.get("ranked_opportunities") or latest_result.get("candidate_opportunities")):
        return latest_result

    if workflows and workflows[0].get("status") in {"completed", "awaiting_approval"}:
        try:
            full_data = get_counseling_session(workflows[0]["id"])
            if full_data and (full_data.get("ranked_opportunities") or full_data.get("candidate_opportunities")):
                st.session_state["workflow_result"] = full_data
                st.session_state["counseling_result"] = full_data
                st.session_state["current_workflow_id"] = workflows[0]["id"]
                return full_data
        except Exception:
            pass
    return latest_result


# ---------------------------------------------------------------------------
# Journey State Evaluation
# ---------------------------------------------------------------------------


def _evaluate_journey(
    profile: dict | None,
    session_data: dict | None,
    opportunities: list[dict],
) -> tuple[int, int, list[dict]]:
    """
    Evaluates where the student is across the 5 stages:
      1. Profile & Records
      2. AI Counseling & Program Matching
      3. Opportunity Shortlist & Deadlines
      4. Document Studio (SOP & Outreach)
      5. Application Tracker & Submission
    Returns: (current_stage_index [1..5], progress_percentage [0..100], steps_metadata)
    """
    has_profile = is_profile_complete(profile)
    ranked_opps = (session_data or {}).get("ranked_opportunities") or []
    has_counseling = len(ranked_opps) > 0

    saved_opps = st.session_state.get("saved_opportunities", {})
    has_shortlist = len(saved_opps) > 0 or has_counseling

    steps = [
        {
            "num": 1,
            "title": "Academic Profile",
            "desc": "GPA, degree, test scores & transcripts",
            "page": "pages/profile.py",
            "status": "completed" if has_profile else "active",
            "status_label": f"{profile.get('target_degree', 'Verified')} ✓" if has_profile and profile else "Action Required",
            "btn_label": "View Profile ↗" if has_profile else "Set Up Profile →",
        },
        {
            "num": 2,
            "title": "Opportunity Discovery",
            "desc": "AI multi-agent matching & Reach/Target scoring",
            "page": "pages/discover.py",
            "status": "completed" if has_counseling else ("active" if has_profile else "pending"),
            "status_label": f"{len(ranked_opps)} Matches Ranked ✓" if has_counseling else ("Ready to Deploy" if has_profile else "Locked"),
            "btn_label": "View Matches ↗" if has_counseling else "Discover Opportunities →",
        },
        {
            "num": 3,
            "title": "Opportunity Shortlist",
            "desc": "Funding, faculty labs & upcoming deadlines",
            "page": "pages/discover.py",
            "status": "completed" if len(saved_opps) >= 2 else ("active" if has_counseling else "pending"),
            "status_label": f"{len(saved_opps)} Saved" if saved_opps else ("Catalog Ready" if has_counseling else "Pending"),
            "btn_label": "Explore Programs ↗",
        },
        {
            "num": 4,
            "title": "Document Studio",
            "desc": "Faculty-grounded SOPs & cold emails",
            "page": "pages/sop.py",
            "status": "active" if has_counseling else "pending",
            "status_label": "AI Drafting Ready" if has_counseling else "Pending",
            "btn_label": "Draft SOP ↗",
        },
        {
            "num": 5,
            "title": "Admissions Tracker",
            "desc": "Deadlines, LORs & submission checklist",
            "page": "pages/tracker.py",
            "status": "active" if has_counseling else "pending",
            "status_label": "Kanban Ready" if has_counseling else "Pending",
            "btn_label": "Open Tracker ↗",
        },
    ]

    if not has_profile:
        current_stage = 1
        progress = 15
    elif not has_counseling:
        current_stage = 2
        progress = 40
    elif not saved_opps:
        current_stage = 3
        progress = 65
    else:
        current_stage = 4
        progress = 85

    return current_stage, progress, steps


# ---------------------------------------------------------------------------
# Tier 1: Hero Bar & Dynamic Next-Step Banner
# ---------------------------------------------------------------------------


def _render_hero_bar(profile: dict | None, completion: int) -> None:
    user = st.session_state.get("current_user")
    raw_name = (profile or {}).get("name") or (user or {}).get("name") or "Student"
    first_name = raw_name.split()[0] if raw_name != "Student" else raw_name

    gpa = (profile or {}).get("gpa")
    gpa_str = f"GPA {gpa}/4.0" if gpa else "GPA Pending"
    major = (profile or {}).get("field_of_study") or "Computer Science"
    degree = (profile or {}).get("current_degree") or (profile or {}).get("academic_level") or "Undergraduate"
    target_deg = (profile or {}).get("target_degree") or "PhD"

    all_tags = ((profile or {}).get("skills") or []) + ((profile or {}).get("projects") or [])
    def _find_tag(pfx: str) -> str | None:
        for t in all_tags:
            if t.lower().startswith(pfx.lower()):
                parts = t.split(":", 1)
                if len(parts) > 1 and parts[1].strip() and parts[1].strip().upper() != "N/A":
                    return parts[1].strip()
        return None

    scores_chips = []
    ssc = (profile or {}).get("ssc_result") or _find_tag("SSC")
    hsc = (profile or {}).get("hsc_result") or _find_tag("HSC")
    gre = (profile or {}).get("gre_score") or (profile or {}).get("gre") or _find_tag("GRE")
    ielts = (profile or {}).get("ielts_score") or (profile or {}).get("ielts") or _find_tag("IELTS")
    sat = (profile or {}).get("sat_score") or _find_tag("SAT")

    if ssc:
        scores_chips.append(f'<span class="ep-cred-chip" style="background: rgba(16, 185, 129, 0.12); border-color: rgba(16, 185, 129, 0.25); color: #6EE7B7;">SSC {ssc}</span>')
    if hsc:
        scores_chips.append(f'<span class="ep-cred-chip" style="background: rgba(16, 185, 129, 0.12); border-color: rgba(16, 185, 129, 0.25); color: #6EE7B7;">HSC {hsc}</span>')
    if gre and gre.upper() != "N/A":
        scores_chips.append(f'<span class="ep-cred-chip">GRE {gre.split()[0]}</span>')
    if ielts and ielts.upper() != "N/A":
        scores_chips.append(f'<span class="ep-cred-chip">IELTS {ielts.split()[0]}</span>')
    if sat and sat.upper() != "N/A":
        scores_chips.append(f'<span class="ep-cred-chip">SAT {sat.split()[0]}</span>')

    extra_chips_html = "".join(scores_chips)

    _html(
        f"""
        <div class="ep-command-hero">
            <div class="ep-hero-header">
                <div class="ep-hero-title-row">
                    <div class="ep-hero-avatar">{first_name[:1].upper()}</div>
                    <div>
                        <div class="ep-hero-greeting">{greeting_for_now()}, {first_name} 👋</div>
                        <div class="ep-hero-sub">Step-by-Step Admissions Roadmap · Targeting {target_deg} Programs</div>
                    </div>
                </div>
                <div class="ep-live-pill">
                    <span class="ep-live-dot"></span>
                    <span>Live Synchronized</span>
                </div>
            </div>

            <div class="ep-hero-credentials">
                <span class="ep-cred-chip" style="background: rgba(16, 185, 129, 0.15); border-color: rgba(16, 185, 129, 0.3); color: #6EE7B7;">{gpa_str} ✓</span>
                <span class="ep-cred-chip">{major}</span>
                <span class="ep-cred-chip">{degree}</span>
                {extra_chips_html}
                <span class="ep-cred-chip" style="margin-left: auto; background: rgba(99, 102, 241, 0.2); border-color: rgba(99, 102, 241, 0.4); color: #C7D2FE;">
                    {completion}% Academic Portfolio Ready
                </span>
            </div>
        </div>
        """
    )


def _render_next_step_callout(current_stage: int, session_data: dict | None) -> None:
    ranked_count = len((session_data or {}).get("ranked_opportunities") or [])

    if current_stage == 1:
        badge = "PHASE 1: ACADEMIC CREDENTIALS"
        title = "Complete Your Academic Background Profile"
        desc = "EduPath AI needs your GPA, field of study, and degree records to calibrate university cutoffs and funding eligibility."
        btn_label = "Complete Academic Profile →"
        target_page = "pages/profile.py"
    elif current_stage == 2:
        badge = "PHASE 2: OPPORTUNITY DISCOVERY"
        title = "Discover Matched Universities, Scholarships & Professors"
        desc = "Your academic profile is ready! Search matched Reach, Target, and Safe opportunities tailored to your degree and target country."
        btn_label = "✦ Discover Opportunities →"
        target_page = "pages/discover.py"
    elif current_stage == 3:
        badge = "PHASE 3: STRATEGY & SHORTLIST"
        title = f"Review Your Discovered Programs ({ranked_count} Matches)"
        desc = "Review your matched universities, faculty alignment, and funding options, and shortlist your top target programs."
        btn_label = "✦ View Discovered Opportunities →"
        target_page = "pages/discover.py"
    else:
        badge = "PHASE 4: APPLICATION PREPARATION"
        title = "Draft Your Tailored Statement of Purpose (SOP)"
        desc = "Use the Document Studio to generate institution-specific SOPs grounded in your actual publications, research experience, and faculty labs."
        btn_label = "Open Document Studio (SOP) →"
        target_page = "pages/sop.py"

    col_box, col_btn = st.columns([2.6, 1])
    with col_box:
        _html(
            f"""
            <div class="ep-next-action-card" style="margin-bottom: 0;">
                <div>
                    <div class="ep-next-action-badge">{badge}</div>
                    <div class="ep-next-action-title">{title}</div>
                    <div class="ep-next-action-desc">{desc}</div>
                </div>
            </div>
            """
        )
    with col_btn:
        st.write("")
        st.write("")
        if st.button(btn_label, type="primary", use_container_width=True, icon=":material/auto_awesome:", key="next-step-primary-btn"):
            if session_data and session_data.get("workflow_id"):
                st.session_state["current_workflow_id"] = session_data.get("workflow_id")
            st.switch_page(target_page)


# ---------------------------------------------------------------------------
# Tier 2: 5-Stage Guided Journey Stepper
# ---------------------------------------------------------------------------


def _render_journey_stepper(current_stage: int, progress: int, steps: list[dict]) -> None:
    _html(
        f"""
        <div class="ep-journey-wrapper">
            <div class="ep-journey-header">
                <div>
                    <div class="ep-journey-title">Admissions Roadmap & Step-by-Step Application Funnel</div>
                    <div class="ep-journey-sub">Stage {current_stage} of 5 Active · Track your end-to-end study-abroad progression</div>
                </div>
                <div style="font-size: 0.95rem; font-weight: 800; color: #4F46E5;">{progress}% Progress</div>
            </div>

            <div class="ep-journey-progress-track">
                <div class="ep-journey-progress-bar" style="width: {progress}%;"></div>
            </div>
        </div>
        """
    )

    # 5-Step Interactive Row
    cols = st.columns(5)
    for col, s in zip(cols, steps, strict=True):
        num = s["num"]
        num_icon = "✓" if s["status"] == "completed" else str(num)
        status_cls = s["status"]
        with col:
            _html(
                f"""
                <div class="ep-journey-card {status_cls}" style="height: 160px; margin-bottom: 0.5rem;">
                    <div>
                        <div class="ep-step-top">
                            <div class="ep-step-number {status_cls}">{num_icon}</div>
                            <span class="ep-step-status-chip {status_cls}">{s['status_label']}</span>
                        </div>
                        <div class="ep-step-title">{s['title']}</div>
                        <div class="ep-step-desc">{s['desc']}</div>
                    </div>
                </div>
                """
            )
            if st.button(s["btn_label"], key=f"step-btn-{num}", use_container_width=True):
                st.switch_page(s["page"])


# ---------------------------------------------------------------------------
# Tier 3: Balanced Supportive Command Workspace
# ---------------------------------------------------------------------------


def _render_executive_briefing(session_data: dict | None) -> None:
    section_header("Active Strategy & Top Recommendations", "Synthesized by your 7-agent AI team.")

    if not session_data or not session_data.get("candidate_opportunities"):
        render_empty_state(
            "No active AI counseling strategy yet",
            "Launch your first counseling session to generate verified university recommendations, faculty matches, and funding strategies.",
            icon="✦",
            cta_label="Discover Opportunities",
            cta_page="pages/discover.py",
            key="empty-strategy-briefing",
        )
        return

    candidates = session_data.get("candidate_opportunities") or []
    ranked = session_data.get("ranked_opportunities") or []
    top_cand = candidates[0] if candidates else {}

    school_title = top_cand.get("title") or top_cand.get("university_name") or "Recommended University"
    degree_field = f"{top_cand.get('degree_level', 'Graduate')} in {top_cand.get('field_of_study', 'Computer Science')}"
    country = top_cand.get("country") or "Global"
    funding = top_cand.get("funding_type") or "Fully Funded (RA/TA/Fellowship)"

    top_score_num = round(ranked[0].get("overall_score", 0.85) * 100) if ranked else 92

    reach_cnt = max(1, len(candidates) // 3)
    target_cnt = max(1, len(candidates) - reach_cnt - 1)
    safe_cnt = max(1, len(candidates) - reach_cnt - target_cnt)

    _html(
        f"""
        <div class="ep-briefing-card">
            <div class="ep-briefing-header">
                <div>
                    <span class="ep-badge indigo" style="margin-bottom: 0.4rem;">Top AI Recommendation</span>
                    <div class="ep-briefing-school">{school_title}</div>
                    <div class="ep-briefing-meta">{degree_field} · {country}</div>
                </div>
                <div style="text-align: right;">
                    <div style="font-size: 1.4rem; font-weight: 800; color: #4F46E5;">{top_score_num}%</div>
                    <div style="font-size: 0.72rem; color: #64748B; font-weight: 600; text-transform: uppercase;">Composite Fit</div>
                </div>
            </div>

            <div style="display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 0.85rem;">
                <span class="ep-badge success">💰 {funding}</span>
                <span class="ep-badge neutral">🏛 Verified Accredited</span>
                <span class="ep-badge neutral">📅 Fall 2027</span>
            </div>

            <div class="ep-tier-distribution">
                <div class="ep-tier-legend">
                    <span>Reach ({reach_cnt})</span>
                    <span>Target ({target_cnt})</span>
                    <span>Safe ({safe_cnt})</span>
                </div>
                <div class="ep-tier-bar-wrapper">
                    <div class="ep-tier-segment-reach" style="width: 33%;"></div>
                    <div class="ep-tier-segment-target" style="width: 45%;"></div>
                    <div class="ep-tier-segment-safe" style="width: 22%;"></div>
                </div>
            </div>
        </div>
        """
    )

    # Top 3 program cards with quick access
    st.markdown("**Top Ranked Programs on Record**")
    cols = st.columns(min(3, len(candidates)))
    for idx, (col, cand) in enumerate(zip(cols, candidates[:3], strict=False)):
        c_title = cand.get("title") or cand.get("university_name") or "University"
        c_country = cand.get("country") or "International"
        c_funding = cand.get("funding_type") or "Funding Available"
        with col:
            _html(
                f"""
                <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 10px; padding: 0.85rem; height: 100%;">
                    <div style="font-size: 0.72rem; color: #6366F1; font-weight: 700; text-transform: uppercase;">Rank #{idx + 1}</div>
                    <div style="font-size: 0.92rem; font-weight: 800; color: #0F172A; margin: 0.2rem 0;">{c_title[:24]}</div>
                    <div style="font-size: 0.76rem; color: #64748B; margin-bottom: 0.4rem;">{c_country}</div>
                    <span class="ep-badge success" style="font-size: 0.68rem;">{c_funding[:20]}</span>
                </div>
                """
            )

    st.write("")
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        if st.button("Open Full Strategy Report →", type="primary", use_container_width=True, key="briefing-open-report"):
            if session_data and session_data.get("workflow_id"):
                st.session_state["current_workflow_id"] = session_data.get("workflow_id")
            st.switch_page("pages/discover.py")
    with col_v2:
        st.page_link("pages/discover.py", label="Explore AI Counseling & Matches →", icon=":material/auto_awesome:", use_container_width=True)


def _render_session_history(workflows: list[dict]) -> None:
    section_header("AI Counseling History", f"{len(workflows)} session(s) recorded.")
    if not workflows:
        st.caption("No past sessions found.")
        return

    for wf in workflows[:4]:
        wf_id = wf.get("id", "")
        short_id = wf_id[:8] if wf_id else "—"
        created = (wf.get("created_at") or "")[:10]
        status = wf.get("status", "completed")
        badge_style = "success" if status == "completed" else ("warning" if status == "awaiting_approval" else "indigo")
        req = (wf.get("user_request") or "AI Counseling Session")[:50]

        _html(
            f"""
            <div class="ep-session-row" style="margin-bottom: 0.5rem;">
                <div class="ep-session-main">
                    <div class="ep-session-title">{req}...</div>
                    <div class="ep-session-meta">ID: {short_id} • Date: {created}</div>
                </div>
                <div class="ep-session-actions">
                    <span class="ep-badge {badge_style}">{status.replace('_', ' ').title()}</span>
                </div>
            </div>
            """
        )
        if st.button(f"Open Session ({short_id}) →", key=f"hist-wf-{wf_id}", use_container_width=True):
            st.session_state["current_workflow_id"] = wf_id
            st.session_state.pop("counseling_result", None)
            st.switch_page("pages/discover.py")


def _render_upcoming_deadlines(opportunities: list[dict]) -> None:
    section_header("Upcoming Deadlines", "Priority application dates on record.")
    if not opportunities:
        st.caption("No deadlines on record yet.")
        return

    upcoming = sorted(
        opportunities,
        key=lambda opp: (days_until(opp.get("deadline")) is None, days_until(opp.get("deadline")) or 0),
    )[:3]

    for opp in upcoming:
        school = opp.get("university_name") or opp.get("institution") or opp.get("title") or "University"
        deadline = opp.get("deadline") or "TBD"
        days_left = days_until(deadline)
        is_urgent = days_left is not None and days_left <= 30
        tag_cls = "urgent" if is_urgent else "normal"
        tag_text = f"{days_left}d left" if days_left is not None else "Open"

        _html(
            f"""
            <div class="ep-deadline-row">
                <div>
                    <div class="ep-deadline-school">{school[:26]}</div>
                    <div class="ep-deadline-sub">Deadline: {deadline}</div>
                </div>
                <span class="ep-countdown-tag {tag_cls}">{tag_text}</span>
            </div>
            """
        )

    st.write("")
    if st.button("Explore Opportunity Catalog →", use_container_width=True, key="deadlines-explore-btn"):
        st.switch_page("pages/counseling.py")


# ---------------------------------------------------------------------------
# Main Page Render
# ---------------------------------------------------------------------------


def render() -> None:
    profile = st.session_state.get("profile")
    profile_id = st.session_state.get("profile_id")
    completion = profile_completion(profile)

    opportunities, _ = _load_catalog()
    workflows = _load_workflows(profile_id)
    session_data = _hydrate_latest_session(workflows)

    render_page_header(
        "Student Admissions Command Center",
        "Your step-by-step application roadmap, matching intelligence, and document pipeline.",
        eyebrow="Admissions Funnel",
    )

    # 1. Hero Intelligence Header
    _render_hero_bar(profile, completion)
    st.write("")

    # 2. Evaluate Student Journey State
    current_stage, progress, steps = _evaluate_journey(profile, session_data, opportunities)

    # 3. Dynamic Recommended Next Step Callout
    _render_next_step_callout(current_stage, session_data)
    st.write("")

    # 4. 5-Stage Guided Journey Stepper (Interactive)
    _render_journey_stepper(current_stage, progress, steps)
    st.write("")

    # 5. Supportive Workspace (Left: Strategy Briefing, Right: Deadlines)
    col_left, col_right = st.columns([1.35, 0.95], gap="large")

    with col_left:
        _render_executive_briefing(session_data)
        st.write("")
        _render_session_history(workflows)

    with col_right:
        _render_upcoming_deadlines(opportunities)


render()
