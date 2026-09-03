from __future__ import annotations

import streamlit as st

from components.empty_state import render_empty_state
from components.header import render_page_header
from utils.session import APPLICATION_STAGES, set_application_stage


def render() -> None:
    render_page_header(
        "Application Tracker",
        "Track each saved opportunity through your application pipeline.",
        eyebrow="Tracker",
    )
    st.caption(
        "This board is stored in your browser session only -- the backend doesn't yet "
        "support persisting application status, so it resets if you restart the app."
    )

    saved = st.session_state.get("saved_opportunities", {})
    stages = st.session_state.get("application_stage", {})

    if not saved:
        render_empty_state(
            "Nothing to track yet",
            "Save an opportunity first, then track its progress through your application pipeline here.",
            icon="🗂️",
            cta_label="Explore Opportunities & Matches",
            cta_page="pages/counseling.py",
            key="tracker-empty",
        )
        return

    columns = st.columns(len(APPLICATION_STAGES))
    for column, stage in zip(columns, APPLICATION_STAGES, strict=True):
        with column:
            opportunity_ids = [oid for oid, s in stages.items() if s == stage and oid in saved]
            st.markdown(f'<div class="ep-section-title" style="font-size:0.85rem;">{stage}</div>', unsafe_allow_html=True)
            st.caption(f"{len(opportunity_ids)} item(s)")
            for opportunity_id in opportunity_ids:
                _render_tracker_card(saved[opportunity_id], stage)


def _render_tracker_card(opportunity: dict, current_stage: str) -> None:
    opportunity_id = opportunity.get("id")
    with st.container(key=f"tracker-card-{opportunity_id}", border=True):
        st.markdown(f'<div class="ep-field-value" style="font-size:0.85rem;">{opportunity.get("title") or "Untitled"}</div>', unsafe_allow_html=True)
        if opportunity.get("university"):
            st.caption(opportunity["university"])
        new_stage = st.selectbox(
            "Stage",
            APPLICATION_STAGES,
            index=APPLICATION_STAGES.index(current_stage),
            key=f"tracker-stage-{opportunity_id}",
            label_visibility="collapsed",
        )
        if new_stage != current_stage:
            set_application_stage(opportunity_id, new_stage)
            st.rerun()


render()
