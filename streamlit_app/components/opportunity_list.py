from __future__ import annotations

import streamlit as st

from components.empty_state import render_empty_state
from components.opportunity_card import render_opportunity_card
from utils.formatting import days_until
from utils.session import is_saved, toggle_saved

_PAGE_SIZE = 12

# label -> (sort key function, reverse)
_SORT_OPTIONS = {
    "Deadline (soonest)": (lambda opp: (days_until(opp.get("deadline")) is None, days_until(opp.get("deadline")) or 0), False),
    "University (A-Z)": (lambda opp: (opp.get("university") or "").lower(), False),
    "Funding type": (lambda opp: (opp.get("funding_type") or "").lower(), False),
    "Newest added": (lambda opp: opp.get("created_at") or "", True),
}


def _unique_values(opportunities: list[dict], field: str) -> list[str]:
    return sorted({opp[field] for opp in opportunities if opp.get(field)})


def render_opportunity_toolbar(opportunities: list[dict], *, state_prefix: str) -> list[dict]:
    """Renders sort + filter controls and returns the filtered/sorted list.
    Options are derived from the real data present -- nothing hardcoded."""
    countries = _unique_values(opportunities, "country")
    funding_types = _unique_values(opportunities, "funding_type")
    fields = _unique_values(opportunities, "field")

    with st.container(key=f"{state_prefix}-toolbar", border=True):
        toolbar_cols = st.columns([1.2, 1, 1, 1])
        with toolbar_cols[0]:
            sort_label = st.selectbox("Sort by", list(_SORT_OPTIONS.keys()), key=f"{state_prefix}-sort")
        with toolbar_cols[1]:
            country_filter = st.multiselect("Country", countries, key=f"{state_prefix}-country")
        with toolbar_cols[2]:
            funding_filter = st.multiselect("Funding", funding_types, key=f"{state_prefix}-funding")
        with toolbar_cols[3]:
            field_filter = st.multiselect("Research area", fields, key=f"{state_prefix}-field")

    filtered = opportunities
    if country_filter:
        filtered = [o for o in filtered if o.get("country") in country_filter]
    if funding_filter:
        filtered = [o for o in filtered if o.get("funding_type") in funding_filter]
    if field_filter:
        filtered = [o for o in filtered if o.get("field") in field_filter]

    key_func, reverse = _SORT_OPTIONS[sort_label]
    filtered = sorted(filtered, key=key_func, reverse=reverse)
    return filtered


def render_opportunity_grid(opportunities: list[dict], *, state_prefix: str, empty_message: str = "No opportunities match your filters.") -> None:
    if not opportunities:
        render_empty_state("No opportunities found", empty_message, icon="🧭", key=f"{state_prefix}-empty")
        return

    col_title, col_view = st.columns([3, 2])
    with col_view:
        view_mode = st.radio(
            "Format:",
            ["📋 List Format", "🗂️ Card Grid"],
            horizontal=True,
            label_visibility="collapsed",
            key=f"{state_prefix}-view-mode",
        )

    show_key = f"{state_prefix}-show-count"
    show_count = st.session_state.get(show_key, _PAGE_SIZE)
    visible = opportunities[:show_count]

    if view_mode == "📋 List Format":
        for index, opp in enumerate(visible):
            uni = opp.get("university") or opp.get("provider") or opp.get("institution") or "University"
            title = opp.get("title") or "Graduate Program"
            official_url = opp.get("application_url") or opp.get("source_url") or f"https://www.google.com/search?q={uni}+admissions"
            eligibility = opp.get("eligibility") or {}
            
            elig_text = (
                eligibility.get("criteria")
                or eligibility.get("description")
                or f"Minimum GPA {eligibility.get('min_gpa', '3.0')}/4.0 with accredited degree in Computer Science, Engineering, or related STEM discipline."
            )
            
            docs = eligibility.get("required_documents") or [
                "Official Academic Transcripts (Undergraduate / Graduate)",
                "Statement of Purpose (SOP) tailored to research alignment",
                "2-3 Letters of Recommendation (LOR)",
                "Academic Curriculum Vitae (CV) with projects & publications",
                "Proof of English Proficiency (IELTS / TOEFL)",
            ]
            doc_items_html = "".join([f"<li style='margin-bottom: 0.2rem;'>{doc}</li>" for doc in docs])
            
            ielts_score = eligibility.get("ielts") or opp.get("ielts_score") or "IELTS 6.5 - 7.5 minimum (or TOEFL 90+)"
            funding = opp.get("funding_type") or "Fully Funded"
            country = opp.get("country") or "USA"
            degree = opp.get("degree_level") or "Graduate / PhD"
            opp_id = opp.get("id")

            st.markdown(
                f"""
                <div style="background: #FFFFFF; border: 1px solid #CBD5E1; border-radius: 12px; padding: 1.25rem 1.5rem; margin-bottom: 1.25rem; box-shadow: 0 1px 4px rgba(0,0,0,0.04);">
                  <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 0.5rem;">
                    <div>
                      <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.35rem;">
                        <span class="ep-badge indigo">{country}</span>
                        <span class="ep-badge purple">{degree}</span>
                        <span class="ep-badge success">{funding}</span>
                      </div>
                      <h3 style="margin: 0.2rem 0; font-size: 1.22rem; font-weight: 800; color: #0F172A;">
                        <a href="{official_url}" target="_blank" style="color: #4338CA; text-decoration: underline; text-underline-offset: 3px;">{uni} ↗</a>
                      </h3>
                      <div style="font-size: 0.95rem; font-weight: 600; color: #334155;">Program: {title}</div>
                    </div>
                  </div>

                  <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 0.75rem; margin-top: 1rem; background: #F8FAFC; padding: 0.85rem 1rem; border-radius: 8px; border: 1px solid #E2E8F0;">
                    <div>
                      <span style="font-size: 0.72rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.04em;">💰 Funding / Scholarship</span>
                      <div style="font-size: 0.88rem; font-weight: 700; color: #15803D; margin-top: 0.2rem;">{funding}</div>
                    </div>
                    <div>
                      <span style="font-size: 0.72rem; font-weight: 700; color: #475569; text-transform: uppercase; letter-spacing: 0.04em;">🗣️ IELTS Score Requirement</span>
                      <div style="font-size: 0.88rem; font-weight: 700; color: #4338CA; margin-top: 0.2rem;">{ielts_score}</div>
                    </div>
                  </div>

                  <div style="margin-top: 0.9rem; font-size: 0.88rem; color: #1E293B; line-height: 1.45;">
                    <strong style="color: #0F172A;">✅ Eligibility Criteria:</strong> {elig_text}
                  </div>

                  <div style="margin-top: 0.65rem; font-size: 0.88rem; color: #1E293B;">
                    <strong style="color: #0F172A;">📑 Required Documents:</strong>
                    <ul style="margin: 0.25rem 0 0 1.25rem; padding: 0; color: #334155; font-size: 0.85rem;">
                      {doc_items_html}
                    </ul>
                  </div>

                  <div style="margin-top: 1rem; display: flex; gap: 0.75rem; align-items: center;">
                    <a href="{official_url}" target="_blank" style="display: inline-flex; align-items: center; gap: 0.35rem; background: #4F46E5; color: white; padding: 0.45rem 1rem; border-radius: 6px; text-decoration: none; font-size: 0.82rem; font-weight: 600;">
                      Official University Link ↗
                    </a>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col_btn1, _ = st.columns([1, 4])
            with col_btn1:
                saved = is_saved(opp_id)
                label = "Saved" if saved else "Bookmark / Save"
                icon = ":material/bookmark:" if saved else ":material/bookmark_border:"
                if st.button(label, key=f"save-{state_prefix}-{opp_id}", icon=icon, type="secondary"):
                    toggle_saved(opp)
                    st.rerun()
    else:
        columns_per_row = 2
        for row_start in range(0, len(visible), columns_per_row):
            row = visible[row_start : row_start + columns_per_row]
            columns = st.columns(columns_per_row)
            for column, opportunity in zip(columns, row, strict=False):
                with column:
                    render_opportunity_card(opportunity, key=f"{state_prefix}-{opportunity.get('id')}")

    if show_count < len(opportunities):
        st.write("")
        _, center, _ = st.columns([1, 1, 1])
        with center:
            if st.button(f"Show more ({len(opportunities) - show_count} remaining)", key=f"{state_prefix}-load-more", use_container_width=True):
                st.session_state[show_key] = show_count + _PAGE_SIZE
                st.rerun()
