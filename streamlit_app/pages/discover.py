from __future__ import annotations

import streamlit as st

from api.client import BackendError, analyze_counseling, list_opportunities, list_opportunities_cached
from components.common import render_backend_error, section_header
from components.empty_state import render_empty_state
from components.header import render_page_header
from components.opportunity_list import render_opportunity_grid, render_opportunity_toolbar
from components.workflow_status import render_workflow_status

_EXAMPLE_REQUEST = "I want fully funded PhD opportunities in AI and Machine Learning in the USA for Fall 2027."

_DEGREE_OPTIONS = ["Any", "BSc", "MSc", "PhD", "Postdoctoral"]
_FUNDING_OPTIONS = ["Any", "Fully Funded", "Partially Funded", "Self-Funded"]
_DEADLINE_OPTIONS = ["Any timeframe", "Next 3 months", "Next 6 months", "Next 12 months"]
_COUNTRY_OPTIONS = ["USA", "Canada", "UK", "Germany", "Australia", "Netherlands", "Sweden", "Switzerland"]
_RESEARCH_OPTIONS = [
    "Artificial Intelligence", "Machine Learning", "Deep Learning",
    "Natural Language Processing", "Computer Vision", "Robotics",
    "Data Science", "Cybersecurity", "Bioinformatics",
]


def render() -> None:
    saved = st.session_state.get("saved_opportunities", {})
    saved_count = len(saved)

    render_page_header(
        "Academic Opportunities Hub",
        "Discover global programs, match with faculty, and manage your saved bookmarks.",
        eyebrow="Opportunities",
    )

    tab_discover, tab_saved = st.tabs([
        ":material/search: Discover Catalog",
        f":material/bookmark: Saved Bookmarks ({saved_count})",
    ])

    with tab_discover:
        _render_discover_tab()

    with tab_saved:
        _render_saved_tab(saved)


def _render_discover_tab() -> None:
    profile_id = st.session_state.get("profile_id")
    if not profile_id:
        render_empty_state(
            "Create your profile first",
            "EduPath AI needs your academic background and goals to run a personalized discovery search.",
            icon="🧑‍🎓",
            cta_label="Complete Profile",
            cta_page="pages/profile.py",
            key="discover-no-profile",
        )
        return

    _render_search_panel(profile_id)

    if st.session_state.get("workflow_error"):
        render_backend_error(st.session_state["workflow_error"], key="workflow")

    if st.session_state.get("workflow_result"):
        st.divider()
        render_workflow_status(st.session_state["workflow_result"])

    st.divider()
    _render_catalog_section()


def _render_search_panel(profile_id: str) -> None:
    with st.container(key="discover-search-panel", border=True):
        user_request = st.text_area(
            "What are you looking for?",
            value=st.session_state.get("last_user_request") or "",
            placeholder=_EXAMPLE_REQUEST,
            height=90,
        )

        with st.expander("Quick filters (optional)", icon=":material/tune:"):
            filter_cols = st.columns(2)
            with filter_cols[0]:
                degree = st.pills("Degree", _DEGREE_OPTIONS, default="Any", key="filter-degree")
                funding = st.pills("Funding", _FUNDING_OPTIONS, default="Any", key="filter-funding")
                deadline_window = st.selectbox("Deadline", _DEADLINE_OPTIONS, key="filter-deadline")
            with filter_cols[1]:
                countries = st.multiselect("Country", _COUNTRY_OPTIONS, key="filter-country")
                research_areas = st.multiselect("Research Area", _RESEARCH_OPTIONS, key="filter-research")

        run = st.button("✦ Discover Opportunities", type="primary", use_container_width=True)

    if run:
        request_text = user_request.strip() or _EXAMPLE_REQUEST
        enriched_request = _compose_request(
            request_text,
            degree=degree,
            funding=funding,
            deadline_window=deadline_window,
            countries=countries,
            research_areas=research_areas,
        )
        st.session_state["last_user_request"] = user_request.strip()
        _run_workflow(profile_id, enriched_request)


def _compose_request(base_request: str, *, degree: str, funding: str, deadline_window: str, countries: list[str], research_areas: list[str]) -> str:
    preferences = []
    if degree and degree != "Any":
        preferences.append(f"Degree: {degree}")
    if funding and funding != "Any":
        preferences.append(f"Funding: {funding}")
    if deadline_window and deadline_window != "Any timeframe":
        preferences.append(f"Deadline window: {deadline_window}")
    if countries:
        preferences.append(f"Countries: {', '.join(countries)}")
    if research_areas:
        preferences.append(f"Research areas: {', '.join(research_areas)}")

    list_spec = (
        " For each matched opportunity, discover and present in a structured list format: "
        "University Name & Official Link, Eligibility Criteria, Required Documents (transcripts, SOP, LORs, CV), "
        "and Minimum IELTS / English Proficiency score."
    )
    if not preferences:
        return f"{base_request}{list_spec}"
    return f"{base_request}\n\nAdditional preferences -- {'; '.join(preferences)}.{list_spec}"


def _run_workflow(profile_id: str, user_request: str) -> None:
    st.session_state["workflow_error"] = None
    payload = {
        "user_request": user_request,
        "student_profile_id": profile_id,
        "workflow_type": "opportunity_discovery",
    }

    with st.status("Running EduPath AI multi-agent workforce...", expanded=True) as status:
        st.write("EduPath AI is coordinating specialized agents (Profile, University, Scholarship, Eligibility, Research) to discover your best matches.")
        try:
            result = analyze_counseling(payload)
        except BackendError as error:
            st.session_state["workflow_error"] = error
            st.session_state["workflow_result"] = None
            status.update(label="Discovery failed", state="error")
            return

        status.update(label="Discovery complete!", state="complete")

    st.session_state["workflow_result"] = result
    st.session_state["current_workflow_id"] = result.get("workflow_id")
    st.session_state["opportunities"] = None
    list_opportunities_cached.clear()
    st.rerun()


def _render_catalog_section() -> None:
    section_header(
        "Opportunity Catalog",
        "Structured opportunities from EduPath AI's database -- sort and filter to explore them.",
    )

    header_cols = st.columns([5, 1])
    with header_cols[1]:
        refresh = st.button("Refresh", icon=":material/refresh:", use_container_width=True)

    if refresh or st.session_state.get("opportunities") is None:
        _load_catalog()

    if st.session_state.get("opportunities_error"):
        render_backend_error(st.session_state["opportunities_error"], key="catalog")
        return

    opportunities = st.session_state.get("opportunities") or []
    if not opportunities:
        render_empty_state(
            "No opportunities in the catalog yet",
            "Check back soon, or try running a discovery search above.",
            icon="🧭",
            key="catalog-empty",
        )
        return

    filtered = render_opportunity_toolbar(opportunities, state_prefix="discover")
    render_opportunity_grid(filtered, state_prefix="discover")


def _load_catalog() -> None:
    st.session_state["opportunities_error"] = None
    try:
        st.session_state["opportunities"] = list_opportunities()
    except BackendError as error:
        st.session_state["opportunities_error"] = error
        st.session_state["opportunities"] = []


def _render_saved_tab(saved: dict) -> None:
    if not saved:
        render_empty_state(
            "No saved opportunities yet",
            "Bookmark programs from the catalog or counseling results to view them here.",
            icon="🔖",
            cta_label="Explore Catalog",
            cta_page="pages/discover.py",
            key="saved-empty",
        )
        return

    opportunities = list(saved.values())

    header_cols = st.columns([5, 1])
    with header_cols[1]:
        if st.button("Clear all", icon=":material/delete_sweep:", use_container_width=True, key="clear-saved-btn"):
            st.session_state["saved_opportunities"] = {}
            st.session_state["application_stage"] = {}
            st.rerun()

    filtered = render_opportunity_toolbar(opportunities, state_prefix="saved")
    render_opportunity_grid(filtered, state_prefix="saved")


render()
