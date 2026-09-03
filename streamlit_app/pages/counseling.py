"""
AI Counseling & Strategy Hub — Synchronized Multi-Agent Workforce Orchestration.
"""
from __future__ import annotations

import streamlit as st

from api.client import BackendError, analyze_counseling, get_counseling_session, list_opportunities_cached, list_workflows
from components.common import render_backend_error, render_html, section_header
from components.empty_state import render_empty_state
from components.header import render_page_header
from components.workflow_status import render_workflow_status

_DEGREE_LEVELS = ["Undergraduate", "Masters", "PhD", "Postdoctoral"]
_FUNDING_OPTIONS = [
    "Fully Funded (RA/TA/Fellowship)",
    "Partial Funding / Tuition Waiver",
    "Self-Funded",
    "Any Funding Available",
]
_INTAKE_OPTIONS = ["Fall 2026", "Spring 2027", "Fall 2027", "Spring 2028", "Flexible"]
_COUNTRY_OPTIONS = [
    "USA", "Canada", "UK", "Germany", "Australia", "Netherlands",
    "Sweden", "Switzerland", "Singapore", "Japan", "France", "Denmark",
    "Finland", "Norway", "Ireland", "South Korea",
]


def _html(content: str) -> None:
    render_html(content)


def _compose_request(profile: dict, calib: dict) -> str:
    name = profile.get("name") or "Applicant"
    major = calib.get("subject_domain") or profile.get("field_of_study") or "Computer Science & Engineering"
    current_deg = profile.get("current_degree") or profile.get("academic_level") or "BSc"
    uni = profile.get("university") or "Accredited Institution"
    target_degree = calib.get("target_degree") or "PhD"
    gpa = profile.get("gpa")

    is_ug = "undergrad" in target_degree.lower()

    parts = [
        f"I am {name}, applying for {target_degree} programs in {major}.",
        f"My current background: {current_deg} from {uni}.",
    ]
    if gpa:
        parts.append(f"My cumulative GPA is {gpa} on a 4.0 scale.")

    # Foundational schooling
    ssc = profile.get("ssc_result")
    hsc = profile.get("hsc_result")
    if ssc:
        parts.append(f"Secondary Schooling (SSC / O-Level): {ssc}.")
    if hsc:
        parts.append(f"Higher Secondary (HSC / A-Level): {hsc}.")

    # Standardized tests
    sat = profile.get("sat_score")
    gre = profile.get("gre_score") or profile.get("gre")
    english = profile.get("english_score") or profile.get("ielts_score") or profile.get("ielts")

    if sat and sat.upper() != "N/A":
        parts.append(f"SAT Score: {sat}.")
    if gre and gre.upper() != "N/A":
        parts.append(f"GRE Score: {gre}.")
    if english and english.upper() != "N/A":
        parts.append(f"English Proficiency: {english}.")

    # Research domains or extracurriculars
    interests = profile.get("research_interests") or []
    if interests:
        parts.append(f"Specialization & research domains: {', '.join(interests) if isinstance(interests, list) else interests}.")

    if profile.get("work_experience"):
        exp_text = profile["work_experience"] if isinstance(profile["work_experience"], str) else ", ".join(profile["work_experience"])
        parts.append(f"Experience / Extracurriculars: {exp_text[:300]}.")

    if profile.get("projects"):
        proj_text = profile["projects"] if isinstance(profile["projects"], str) else ", ".join(profile["projects"])
        parts.append(f"Projects / Achievements: {proj_text[:250]}.")

    if not is_ug and profile.get("publications"):
        pub_text = profile["publications"] if isinstance(profile["publications"], str) else ", ".join(profile["publications"])
        parts.append(f"Peer-Reviewed Publications: {pub_text}.")

    if profile.get("has_msc") or profile.get("msc_university"):
        msc_d = profile.get("msc_degree") or "MSc"
        msc_u = profile.get("msc_university")
        msc_g = profile.get("msc_gpa")
        msc_t = profile.get("msc_thesis")
        msc_str = f"Master's Degree: {msc_d} from {msc_u}"
        if msc_g:
            msc_str += f" (GPA: {msc_g}/4.0)"
        parts.append(f"{msc_str}.")
        if msc_t:
            parts.append(f"Master's Thesis Focus: {msc_t}.")

    if calib.get("special_focus"):
        parts.append(f"Session focus and specific goals: {calib['special_focus']}.")

    target_countries = calib.get("target_countries") or ["USA", "Canada"]
    parts.append(f"Dream destination countries: {', '.join(target_countries)}.")
    parts.append(f"Funding requirements: {calib.get('funding_requirement', 'Fully Funded')}.")
    parts.append(f"Target intake: {calib.get('target_intake', 'Fall 2027')}.")
    parts.append(
        "Find matched universities, scholarships/assistantships, and professors based on my academic profile and demands. "
        "For each match, return: University Name with official link, matched scholarship/assistantship, matched professor/faculty advisor, "
        "eligibility criteria, required documents (transcripts, SOP, LORs, CV), and required minimum IELTS score."
    )
    return " ".join(parts)


def _render_verified_profile_banner(profile: dict) -> None:
    student_name = profile.get("name") or "Student"
    gpa = profile.get("gpa") or "N/A"
    major = profile.get("field_of_study") or "General"
    current_deg = profile.get("current_degree") or profile.get("academic_level") or "Undergraduate"
    uni = profile.get("university") or "Institution"

    all_tags = (profile.get("skills") or []) + (profile.get("projects") or [])
    def _get_tag(pfx: str) -> str | None:
        for t in all_tags:
            if t.lower().startswith(pfx.lower()):
                parts = t.split(":", 1)
                if len(parts) > 1 and parts[1].strip() and parts[1].strip().upper() != "N/A":
                    return parts[1].strip()
        return None

    scores = []
    ssc = profile.get("ssc_result") or _get_tag("SSC")
    if ssc:
        scores.append(f"SSC: {ssc}")
    hsc = profile.get("hsc_result") or _get_tag("HSC")
    if hsc:
        scores.append(f"HSC: {hsc}")
    sat = profile.get("sat_score") or _get_tag("SAT")
    if sat and sat.upper() != "N/A":
        scores.append(f"SAT: {sat}")
    gre = profile.get("gre_score") or profile.get("gre") or _get_tag("GRE")
    if gre and gre.upper() != "N/A":
        scores.append(f"GRE: {gre}")
    ielts = profile.get("ielts_score") or profile.get("ielts") or _get_tag("IELTS")
    if ielts and ielts.upper() != "N/A":
        scores.append(f"IELTS: {ielts}")
    toefl = profile.get("toefl_score") or profile.get("toefl") or _get_tag("TOEFL")
    if toefl and toefl.upper() != "N/A":
        scores.append(f"TOEFL: {toefl}")

    score_text = f" · {' · '.join(scores)}" if scores else ""

    col_meta, col_btn = st.columns([3, 1])
    with col_meta:
        _html(
            f"""
            <div style="background: linear-gradient(135deg, #EEF2FF 0%, #F8FAFC 100%); border: 1px solid #C7D2FE; border-radius: 12px; padding: 0.85rem 1.25rem;">
                <div style="display: flex; align-items: center; justify-content: space-between;">
                    <div style="font-size: 0.72rem; color: #4F46E5; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em;">Synchronized Academic Profile</div>
                    <span class="ep-badge success" style="font-size: 0.72rem;">Verified Record ✓</span>
                </div>
                <div style="font-size: 1rem; font-weight: 800; color: #0F172A; margin-top: 0.2rem;">
                    {student_name} · GPA: {gpa}/4.0 · {major} ({current_deg})
                </div>
                <div style="font-size: 0.82rem; color: #64748B; margin-top: 0.15rem;">
                    Institution: {uni}{score_text}
                </div>
                {f'<div style="font-size: 0.82rem; color: #4338CA; font-weight: 600; margin-top: 0.2rem;">🎓 Master\'s: {profile.get("msc_degree", "MSc")} · {profile.get("msc_university")} (GPA: {profile.get("msc_gpa")}/4.0)</div>' if profile.get("msc_university") else ''}
            </div>
            """
        )
    with col_btn:
        st.write("")
        st.page_link("pages/profile.py", label="Edit Profile Credentials ↗", icon=":material/edit:", use_container_width=True)


def _render_strategy_calibrator(profile: dict, profile_id: str | None) -> None:
    section_header(
        "Strategy Calibration",
        "Your academic record is already loaded. Calibrate your application goals below and deploy the workforce.",
    )

    # Pre-populate defaults from profile where available
    pref_countries = profile.get("target_countries") or ["USA", "Canada"]
    pref_degree = profile.get("target_degree") or "PhD"
    deg_idx = _DEGREE_LEVELS.index(pref_degree) if pref_degree in _DEGREE_LEVELS else 2
    pref_funding = profile.get("preferred_funding") or "Fully Funded (RA/TA/Fellowship)"
    fund_idx = _FUNDING_OPTIONS.index(pref_funding) if pref_funding in _FUNDING_OPTIONS else 0

    with st.container(key="strategy-calibrator-card"):
        col1, col2 = st.columns(2)
        with col1:
            target_degree = st.selectbox("Target Degree Level", _DEGREE_LEVELS, index=deg_idx, help="Graduate or undergraduate program level you are targeting.")
            subject_domain = st.text_input("Subject / Domain Choice *", value=profile.get("field_of_study") or "Computer Science & Engineering", help="Academic discipline or research domain for university matching.")
            target_intake = st.selectbox("Target Intake Term", _INTAKE_OPTIONS, index=2, help="Primary matriculation semester.")
        with col2:
            target_countries = st.multiselect(
                "Dream Destination Countries *",
                _COUNTRY_OPTIONS,
                default=[c for c in pref_countries if c in _COUNTRY_OPTIONS] or ["USA", "Canada"],
                help="Countries where your AI team should search for accredited programs.",
            )
            funding_requirement = st.selectbox(
                "Funding Requirement",
                _FUNDING_OPTIONS,
                index=fund_idx,
                help="Assistantships (RA/TA), university fellowships, or tuition waivers.",
            )

        special_focus = st.text_area(
            "Special Research Focus / Session Objectives (Optional)",
            value="",
            placeholder="e.g. Focus on labs doing Computer Vision & Multimodal Reasoning with active NSF grants, or emphasize DAAD doctoral funding.",
            help="Additional guidance for the supervisor and specialist agents.",
        )

        st.write("")
        col_btn1, col_btn2 = st.columns([1.5, 1])
        with col_btn1:
            deploy_clicked = st.button(
                "✦ Deploy AI Workforce on My Profile",
                type="primary",
                use_container_width=True,
                icon=":material/auto_awesome:",
                key="btn-deploy-workforce",
            )
        with col_btn2:
            st.caption("Coordinates 7 specialist agents via OpenRouter with verified source citations.")

    if deploy_clicked:
        calib_data = {
            "target_degree": target_degree,
            "subject_domain": subject_domain.strip(),
            "target_intake": target_intake,
            "target_countries": target_countries,
            "funding_requirement": funding_requirement,
            "special_focus": special_focus.strip(),
        }
        _execute_counseling_workflow(profile, profile_id, calib_data)


def _execute_counseling_workflow(profile: dict, profile_id: str | None, calib_data: dict) -> None:
    request_text = _compose_request(profile, calib_data)
    payload = {
        "user_request": request_text,
        "workflow_type": "opportunity_discovery",
    }
    if profile_id:
        payload["student_profile_id"] = profile_id

    agents_info = [
        ("Profile Analyst", "👤", "Extracting academic strengths & test signals"),
        ("University Matcher", "🏫", "Discovering global programs aligned with criteria"),
        ("Scholarship Engine", "💰", "Identifying assistantships & merit funding"),
        ("Eligibility Verifier", "✅", "Validating minimum GPA & prerequisite criteria"),
        ("Research Alignment", "🔬", "Semantic mapping of thesis & faculty research"),
        ("Verification Agent", "🔍", "Grounding deadlines & tuition in official sources"),
        ("Ranking Engine", "⭐", "Computing multi-criteria Reach/Target/Safe scores"),
    ]

    with st.status("Deploying AI workforce on your application...", expanded=True) as status:
        for name, icon, desc in agents_info:
            st.write(f"{icon} **{name}**: {desc}...")

        try:
            result = analyze_counseling(payload)
        except BackendError as error:
            st.session_state["counseling_error"] = error
            status.update(label="Counseling workflow encountered an issue", state="error")
            st.rerun()
            return
        status.update(label="Counseling analysis complete! ✦", state="complete")

    st.session_state["counseling_result"] = result
    st.session_state["current_workflow_id"] = result.get("workflow_id")
    st.session_state["workflow_result"] = result
    list_opportunities_cached.clear()
    st.rerun()


def render() -> None:
    profile_id = st.session_state.get("profile_id")
    profile = st.session_state.get("profile")

    # Gate: Student must set up baseline academic profile first
    if not profile_id or not profile or not profile.get("gpa") or not profile.get("field_of_study"):
        render_page_header(
            "AI Counseling Session",
            "Multi-agent academic matching, faculty discovery, and strategy planning.",
            eyebrow="Profile Required",
        )
        render_empty_state(
            "Complete Your Academic Profile First",
            "EduPath AI requires your academic records (GPA, major, degree, and skills) in your profile to calibrate matched programs.",
            icon="🧑‍🎓",
            cta_label="Set Up Academic Profile Now →",
            cta_page="pages/profile.py",
            key="counseling-profile-gate",
        )
        return

    # Check if a workflow ID is set (e.g. from Dashboard "Open ->") and hydrate results
    active_wf_id = st.session_state.get("current_workflow_id")
    if active_wf_id and not st.session_state.get("counseling_result"):
        try:
            wf_data = get_counseling_session(active_wf_id)
            if wf_data and (wf_data.get("ranked_opportunities") or wf_data.get("agent_results")):
                st.session_state["counseling_result"] = wf_data
                st.session_state["workflow_result"] = wf_data
        except Exception:
            pass

    render_page_header(
        "AI Counseling & Opportunities Hub",
        "Synchronized admissions matching, scholarship discovery, professor alignment, and strategy planning.",
        eyebrow="AI Counseling",
    )

    _render_verified_profile_banner(profile)
    st.write("")

    # --- Mode 1: Display Completed Strategy Report ---
    if st.session_state.get("counseling_result"):
        result = st.session_state["counseling_result"]
        render_workflow_status(result)

        st.write("")
        col_r1, col_r2 = st.columns(2)
        with col_r1:
            if st.button("✦ Start New Counseling Strategy", type="primary", use_container_width=True, icon=":material/refresh:"):
                st.session_state.pop("counseling_result", None)
                st.session_state.pop("counseling_error", None)
                st.session_state.pop("current_workflow_id", None)
                st.rerun()
        with col_r2:
            st.page_link("pages/tracker.py", label="View in Application Tracker →", icon=":material/checklist:")
        return

    # --- Mode 2: Error Recovery or Background Completion ---
    if st.session_state.get("counseling_error"):
        if profile_id:
            try:
                workflows = list_workflows(profile_id)
                if workflows and workflows[0].get("status") in {"completed", "awaiting_approval"}:
                    latest_wf = workflows[0]
                    col_info, col_btn = st.columns([2, 1])
                    with col_info:
                        st.info(
                            f"A counseling session completed in the background ({latest_wf.get('id', '')[:8]}).",
                            icon=":material/check_circle:",
                        )
                    with col_btn:
                        if st.button("Load Completed Analysis →", type="primary", use_container_width=True, key="load-bg-counseling"):
                            res = get_counseling_session(latest_wf["id"])
                            st.session_state["counseling_result"] = res
                            st.session_state["workflow_result"] = res
                            st.session_state["current_workflow_id"] = latest_wf["id"]
                            st.session_state.pop("counseling_error", None)
                            st.rerun()
            except Exception:
                pass

        retried = render_backend_error(st.session_state["counseling_error"], key="counseling-analysis")
        if retried:
            st.session_state.pop("counseling_error", None)
            st.rerun()
        return

    # --- Mode 3: Strategy Calibrator (Frictionless Intake) ---
    _render_strategy_calibrator(profile, profile_id)


render()
