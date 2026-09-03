from __future__ import annotations

import streamlit as st
from components.common import render_html


def _html(content: str) -> None:
    render_html(content)


def _find_tagged_score(items: list[str] | None, prefix: str) -> str | None:
    if not items:
        return None
    p = prefix.lower()
    for item in items:
        clean = item.strip()
        if clean.lower().startswith(p):
            parts = clean.split(":", 1)
            if len(parts) > 1 and parts[1].strip() and parts[1].strip().upper() != "N/A":
                return parts[1].strip()
    return None


def render_profile_summary(profile: dict | None) -> None:
    """Renders the comprehensive student academic profile summary card."""
    profile = profile or {}
    all_tags = (profile.get("skills") or []) + (profile.get("projects") or []) + (profile.get("work_experience") or [])

    phone = profile.get("phone") or _find_tagged_score(all_tags, "Phone") or "—"
    ssc = profile.get("ssc_result") or _find_tagged_score(all_tags, "SSC")
    hsc = profile.get("hsc_result") or _find_tagged_score(all_tags, "HSC")
    sat = profile.get("sat_score") or _find_tagged_score(all_tags, "SAT")
    gre = profile.get("gre_score") or _find_tagged_score(all_tags, "GRE")
    english = profile.get("english_score") or profile.get("ielts_score") or _find_tagged_score(all_tags, "English") or _find_tagged_score(all_tags, "IELTS")

    is_ug = "undergrad" in (profile.get("target_degree") or profile.get("academic_level") or "").lower()

    with st.container(key="profile-summary-card", border=True):
        # 1. Identity & Contact Row
        row_id = st.columns(3)
        _field(row_id[0], "Applicant Name", profile.get("name") or "Student")
        _field(row_id[1], "Verified Email", profile.get("email") or "—")
        _field(row_id[2], "Contact Phone", phone)

        # 2. Academic Level & Core Credentials Row
        row_acad = st.columns(3)
        _field(row_acad[0], "Academic Track", profile.get("target_degree") or "PhD")
        _field(row_acad[1], "Discipline / Major", profile.get("field_of_study") or "General")
        _field(row_acad[2], "Cumulative GPA", f"{profile.get('gpa')}/4.0" if profile.get('gpa') else "—")

        # 3. School / University Institution Row
        row_inst = st.columns(2)
        inst_label = "Higher Secondary College" if is_ug else "Undergraduate University"
        _field(row_inst[0], inst_label, profile.get("university") or "—")
        _field(row_inst[1], "Graduation Year", profile.get("graduation_year") or "—")

        # Master's Degree Details (if completed or pursuing for PhD)
        msc_uni = profile.get("msc_university") or _find_tagged_score(all_tags, "MSc")
        if msc_uni:
            msc_title = profile.get("msc_degree") or "MSc Degree"
            msc_gpa = profile.get("msc_gpa")
            gpa_disp = f" · GPA {msc_gpa}/4.0" if msc_gpa else ""
            row_msc = st.columns(2)
            _field(row_msc[0], "Master's Institution & Degree", f"{msc_title} — {msc_uni}{gpa_disp}")
            _field(row_msc[1], "Master's Thesis / Focus", profile.get("msc_thesis") or "—")

        # 4. Foundational Schooling & Test Scores Badge Row
        score_badges = []
        if ssc:
            score_badges.append(f"SSC: {ssc} ✓")
        if hsc:
            score_badges.append(f"HSC: {hsc} ✓")
        if sat and sat.upper() != "N/A":
            score_badges.append(f"SAT: {sat}")
        if gre and gre.upper() != "N/A":
            score_badges.append(f"GRE: {gre}")
        if english and english.upper() != "N/A":
            score_badges.append(f"Language: {english}")

        if score_badges:
            _html('<div class="ep-field-label" style="margin-top: 0.85rem;">Foundational Schooling & Standardized Tests</div>')
            _badge_row(score_badges, style="indigo")

        # 5. Extracurriculars / Experience & Publications
        interests = profile.get("research_interests") or []
        publications = profile.get("publications") or []
        experience = profile.get("work_experience") or []
        projects = profile.get("projects") or []

        if interests and not is_ug:
            _html('<div class="ep-field-label" style="margin-top: 0.65rem;">Primary Research Domain(s)</div>')
            _badge_row(interests, style="purple")

        if publications and not is_ug:
            _html('<div class="ep-field-label" style="margin-top: 0.65rem;">Peer-Reviewed Publications & Preprints</div>')
            _badge_row(publications, style="success", limit=4)

        if experience:
            exp_label = "Extracurricular Activities (ECA) & Leadership" if is_ug else "Work & Lab Research Experience"
            _html(f'<div class="ep-field-label" style="margin-top: 0.65rem;">{exp_label}</div>')
            _badge_row(experience, style="neutral", limit=3)

        if projects and is_ug:
            _html('<div class="ep-field-label" style="margin-top: 0.65rem;">Olympiad / Competition Achievements & Honors</div>')
            _badge_row(projects, style="emerald", limit=3)


def _field(column, label: str, value: object) -> None:
    with column:
        _html(f'<div class="ep-field-label">{label}</div>')
        display = value if value not in (None, "") else "—"
        _html(f'<div class="ep-field-value">{display}</div>')


def _badge_row(items: list[str], *, style: str = "indigo", limit: int = 8) -> None:
    shown = items[:limit]
    extra = len(items) - len(shown)
    badges = "".join(f'<span class="ep-badge {style}">{item}</span>' for item in shown)
    if extra > 0:
        badges += f'<span class="ep-badge neutral">+{extra} more</span>'
    _html(f'<div class="ep-badge-row">{badges}</div>')


def render_completion_bar(completion: int) -> None:
    _html(
        f"""
        <div class="ep-metric-caption" style="margin-bottom:0;">Profile completion: {completion}%</div>
        <div class="ep-progress-track"><div class="ep-progress-fill" style="width:{completion}%"></div></div>
        """
    )
