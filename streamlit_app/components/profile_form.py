"""
Adaptive Student Profile Form.
Enforces 3 distinct student categories:
  1. Undergraduate:
     - Name, Email, Phone Number
     - Secondary Schooling (SSC / O-Level): Group (Science/Business/Arts), Result, School Name, Board, Passing Year
     - Higher Secondary Schooling (HSC / A-Level): Group (Science/Business/Arts), Result, College Name, Board, Passing Year
     - Standardized Tests: SAT / ACT Score, English Proficiency (IELTS / PTE / TOEFL)
     - Intended Undergraduate Major
     - Extracurricular Activities (ECA), Leadership & Olympiad Achievements (UG Only)
     - NO publications required.
  2. Master's (MSc) & PhD:
     - All foundational schooling (SSC/HSC results & institutions)
     - Undergraduate (and Graduate for PhD) Degree Results, Institute Name, Cumulative GPA, Passing Year
     - Research Domain & Subject Specialization
     - Work & Research Lab Experience
     - GRE Score (if taken) & English Proficiency (IELTS / TOEFL / PTE)
     - Existing Publications / Preprints & Capstone Software/Research Projects
Note: Dream destination countries and funding requirements are calibrated in AI Counseling.
"""
from __future__ import annotations

import re
from datetime import UTC, datetime
import streamlit as st

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_DEGREE_CATEGORIES = [
    "Undergraduate (Bachelor's)",
    "Master's (MSc / MA / MBA)",
    "PhD / Doctoral (PhD / Postdoc)",
]

_ACADEMIC_GROUPS = [
    "Science",
    "Business Studies / Commerce",
    "Humanities / Arts",
    "General / Other",
]

_EDUCATION_BOARDS = [
    "Dhaka", "Chattogram", "Rajshahi", "Sylhet", "Barishal",
    "Khulna", "Cumilla", "Dinajpur", "Mymensingh", "Madrasah Board",
    "Technical Board", "Cambridge / Edexcel (UK)", "International Baccalaureate (IB)",
    "CBSE / ICSE (India)", "US High School Board", "Other / International",
]

_ENGLISH_TEST_OPTIONS = [
    "IELTS Academic",
    "TOEFL iBT",
    "PTE Academic",
    "Duolingo English Test (DET)",
    "Medium of Instruction (MOI) Waived",
    "Not Taken Yet / None",
]

_COMMON_RESEARCH_DOMAINS = [
    "Artificial Intelligence & Machine Learning",
    "Computer Vision & Pattern Recognition",
    "Natural Language Processing & Speech",
    "Robotics & Autonomous Systems",
    "Data Science & Big Data Analytics",
    "Software Engineering & Distributed Systems",
    "Cybersecurity, Privacy & Cryptography",
    "Bioinformatics & Computational Biology",
    "Human-Computer Interaction (HCI)",
    "Internet of Things (IoT) & Embedded Systems",
    "Quantum Computing & Information Theory",
    "Renewable Energy & Power Engineering",
    "Biomedical Engineering",
    "Economics, Finance & Management",
]

_COMMON_SKILLS = [
    "Python", "C++", "Java", "PyTorch", "TensorFlow", "SQL", "R",
    "Git", "Docker", "Linux", "AWS", "Data Analysis", "Research Writing",
    "Public Speaking", "Problem Solving", "LaTeX",
]


def _find_tagged(items: list[str] | None, prefix: str, default: str = "") -> str:
    if not items:
        return default
    prefix_lower = prefix.lower()
    for item in items:
        clean = item.strip()
        if clean.lower().startswith(prefix_lower):
            parts = clean.split(":", 1)
            if len(parts) > 1:
                return parts[1].strip()
            return clean
    return default


def _split_list(raw: str) -> list[str]:
    if not raw or not raw.strip():
        return []
    parts = re.split(r"[,\n]", raw)
    return [part.strip() for part in parts if part.strip()]


def _join_list(items: list[str] | None) -> str:
    return ", ".join(items or [])


def _merged_options(base: list[str], existing: list[str] | None) -> list[str]:
    existing = existing or []
    merged = list(base)
    for value in existing:
        if value not in merged and not any(value.lower().startswith(p) for p in ["ssc:", "hsc:", "sat:", "gre:", "ielts:", "toefl:", "pte:", "phone:"]):
            merged.append(value)
    return merged


def _index_of(options: list[str], value: object) -> int:
    if value and value in options:
        return options.index(value)
    return 0


def render_profile_form(existing: dict | None = None) -> dict | None:
    existing = existing or {}
    current_year = datetime.now(UTC).year

    # Extract tagged data from skills or projects or existing dict
    all_tags = (existing.get("skills") or []) + (existing.get("projects") or []) + (existing.get("work_experience") or [])

    existing_phone = existing.get("phone") or _find_tagged(all_tags, "Phone", "+880 1712-345678")
    existing_ssc_res = existing.get("ssc_result") or _find_tagged(all_tags, "SSC Result", "GPA 5.0 / 5.0")
    existing_ssc_school = existing.get("ssc_school") or _find_tagged(all_tags, "SSC School", "Ideal School & College")
    existing_hsc_res = existing.get("hsc_result") or _find_tagged(all_tags, "HSC Result", "GPA 5.0 / 5.0")
    existing_hsc_college = existing.get("hsc_college") or _find_tagged(all_tags, "HSC College", "Notre Dame College")

    existing_sat = existing.get("sat_score") or _find_tagged(all_tags, "SAT", "")
    existing_gre = existing.get("gre_score") or _find_tagged(all_tags, "GRE", "326 (Q: 168, V: 158, AWA: 4.5)")
    existing_english = existing.get("english_score") or existing.get("ielts_score") or _find_tagged(all_tags, "English Test", "IELTS 7.5 (L: 8.0, R: 8.0, W: 7.0, S: 7.0)")

    # Target category
    raw_target = (existing.get("target_degree") or existing.get("academic_level") or "PhD").lower()
    if "undergrad" in raw_target or "bachelor" in raw_target:
        default_cat_idx = 0
    elif "master" in raw_target or "msc" in raw_target:
        default_cat_idx = 1
    else:
        default_cat_idx = 2

    st.markdown('<div class="ep-section-title">Select Student Application Category</div>', unsafe_allow_html=True)
    st.caption("Choose your target degree level. The profile fields adapt to your exact educational stage.")

    degree_category = st.radio(
        "Application Category",
        _DEGREE_CATEGORIES,
        index=default_cat_idx,
        horizontal=True,
        key="profile_degree_category_radio",
        label_visibility="collapsed",
    )

    is_ug = "Undergraduate" in degree_category
    is_msc = "Master" in degree_category
    is_phd = "PhD" in degree_category

    with st.form("profile_form", clear_on_submit=False, border=False):
        # ------------------------------------------------------------------
        # 1. Personal & Contact Information
        # ------------------------------------------------------------------
        st.markdown('<div class="ep-section-title">1. Personal & Contact Information</div>', unsafe_allow_html=True)
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            name = st.text_input("Full Name *", value=existing.get("name") or "", placeholder="e.g. Md. Bakibillah Rahat")
            phone = st.text_input("Phone Number *", value=existing_phone, placeholder="e.g. +880 1712-345678")
        with col_p2:
            email = st.text_input("Email Address *", value=existing.get("email") or "", placeholder="rahat@example.com")
            st.caption("Your contact info is used for verified profile identification and session notifications.")

        st.divider()

        # ------------------------------------------------------------------
        # 2. Secondary Schooling (SSC / O-Level / 10th Grade)
        # ------------------------------------------------------------------
        st.markdown('<div class="ep-section-title">2. Secondary Schooling (SSC / O-Level / 10th Grade)</div>', unsafe_allow_html=True)
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            ssc_exam_type = st.selectbox(
                "Curriculum / Examination",
                ["SSC", "O-Level (Cambridge / Edexcel)", "10th Grade / CBSE / ICSE", "Other"],
                index=_index_of(["SSC", "O-Level (Cambridge / Edexcel)", "10th Grade / CBSE / ICSE", "Other"], existing.get("ssc_exam_type")),
                key="ssc_exam_type",
            )
            ssc_group = st.selectbox(
                "Academic Group / Stream",
                _ACADEMIC_GROUPS,
                index=_index_of(_ACADEMIC_GROUPS, existing.get("ssc_group")),
                key="ssc_group",
            )
            ssc_school = st.text_input("Secondary School Name *", value=existing_ssc_school, placeholder="e.g. Ideal School & College, St. Joseph High School")
        with col_s2:
            ssc_result = st.text_input("SSC / O-Level Result *", value=existing_ssc_res, placeholder="e.g. GPA 5.0 / 5.0, Golden A+, 7 A*s")
            ssc_board = st.selectbox(
                "Education Board",
                _EDUCATION_BOARDS,
                index=_index_of(_EDUCATION_BOARDS, existing.get("ssc_board")),
                key="ssc_board",
            )
            ssc_yr_val = int(existing.get("ssc_year") or min(current_year - 4, 2018))
            ssc_year = st.number_input("SSC Passing Year *", min_value=2000, max_value=current_year, step=1, value=ssc_yr_val, key="ssc_year")

        st.divider()

        # ------------------------------------------------------------------
        # 3. Higher Secondary Schooling (HSC / A-Level / 12th Grade)
        # ------------------------------------------------------------------
        st.markdown('<div class="ep-section-title">3. Higher Secondary Schooling (HSC / A-Level / 12th Grade)</div>', unsafe_allow_html=True)
        col_h1, col_h2 = st.columns(2)
        with col_h1:
            hsc_exam_type = st.selectbox(
                "Curriculum / Examination",
                ["HSC", "A-Level (Cambridge / Edexcel)", "12th Grade / IB Diploma", "Other"],
                index=_index_of(["HSC", "A-Level (Cambridge / Edexcel)", "12th Grade / IB Diploma", "Other"], existing.get("hsc_exam_type")),
                key="hsc_exam_type",
            )
            hsc_group = st.selectbox(
                "Academic Group / Stream",
                _ACADEMIC_GROUPS,
                index=_index_of(_ACADEMIC_GROUPS, existing.get("hsc_group")),
                key="hsc_group",
            )
            hsc_college = st.text_input("Higher Secondary College / School Name *", value=existing_hsc_college, placeholder="e.g. Notre Dame College, Dhaka College")
        with col_h2:
            hsc_result = st.text_input("HSC / A-Level Result *", value=existing_hsc_res, placeholder="e.g. GPA 5.0 / 5.0, Golden A+, A*AA")
            hsc_board = st.selectbox(
                "Education Board",
                _EDUCATION_BOARDS,
                index=_index_of(_EDUCATION_BOARDS, existing.get("hsc_board")),
                key="hsc_board",
            )
            hsc_yr_val = int(existing.get("hsc_year") or min(current_year - 2, 2020))
            hsc_year = st.number_input("HSC Passing / Expected Year *", min_value=2000, max_value=current_year + 3, step=1, value=hsc_yr_val, key="hsc_year")

        st.divider()

        # ------------------------------------------------------------------
        # 4. Standardized Tests & English Language Proficiency
        # ------------------------------------------------------------------
        st.markdown('<div class="ep-section-title">4. Standardized Tests & English Language Proficiency</div>', unsafe_allow_html=True)
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            if is_ug:
                sat_score = st.text_input("SAT / ACT Score (Optional / If taken)", value=existing_sat, placeholder="e.g. SAT: 1480 (Math: 780, EBRW: 700) or N/A")
                gre_score = "N/A"
            else:
                gre_score = st.text_input("GRE Score (If taken / have)", value=existing_gre, placeholder="e.g. 326 (Q: 168, V: 158, AWA: 4.5) or N/A")
                sat_score = "N/A"
        with col_t2:
            english_test_type = st.selectbox("English Proficiency Test", _ENGLISH_TEST_OPTIONS, index=0, key="english_test_type")
            english_score = st.text_input("English Test Score Details", value=existing_english, placeholder="e.g. IELTS 7.5 (L: 8.0, R: 8.0, W: 7.0, S: 7.0), PTE 72, or TOEFL 105")

        st.divider()

        # ------------------------------------------------------------------
        # Conditional Section: Undergraduate vs. Master's / PhD
        # ------------------------------------------------------------------
        if is_ug:
            # ---------------- UNDERGRADUATE APPLICANT ----------------
            st.markdown('<div class="ep-section-title">5. Intended Undergraduate Field & Extracurriculars (ECA)</div>', unsafe_allow_html=True)
            col_u1, col_u2 = st.columns(2)
            with col_u1:
                field_of_study = st.text_input("Intended Undergraduate Major / Domain *", value=existing.get("field_of_study") or "", placeholder="e.g. Computer Science, Mechanical Engineering, Economics")
            with col_u2:
                gpa_val = float(existing.get("gpa") or 3.85)
                gpa = st.number_input("Secondary Converted Cumulative GPA (0.0 - 4.0 scale)", min_value=0.0, max_value=4.0, step=0.01, value=min(max(gpa_val, 0.0), 4.0), help="Scaled secondary GPA used by admissions matching algorithms.")

            st.caption("Undergraduate admissions heavily weigh extracurricular leadership, clubs, volunteering, and Olympiad achievements:")
            eca_details = st.text_area(
                "Extracurricular Activities (ECA) & Leadership Roles *",
                value=_join_list(existing.get("work_experience")) or "President of Science & Robotics Club; Executive Member of Debating Society; Volunteer at Bangladesh Red Crescent Society",
                placeholder="e.g. President of Science Club, Captain of Basketball Team, Active Community Volunteer...",
            )
            achievements = st.text_area(
                "Olympiad / Competition Achievements, Honors & Awards",
                value=_join_list(existing.get("projects")) or "National Math Olympiad Divisional Champion; High School Valedictorian; Best Speaker at Inter-College Debate 2023",
                placeholder="e.g. Divisional Champion at Bangladesh Mathematical Olympiad, Physics Olympiad Medalist...",
            )
            skills = st.multiselect(
                "Key Academic & Technical Skills",
                options=_merged_options(_COMMON_SKILLS, existing.get("skills")),
                default=[s for s in (existing.get("skills") or ["Python", "Public Speaking", "Problem Solving"]) if s in _COMMON_SKILLS],
                accept_new_options=True,
            )

            institution = hsc_college
            current_degree = "High School / HSC"
            graduation_year = int(hsc_year)
            publications_list = []  # No publications required for UG
            work_experience = eca_details

        else:
            # ---------------- MASTER'S & PhD APPLICANTS ----------------
            st.markdown('<div class="ep-section-title">5. Undergraduate & Higher Academic Results</div>', unsafe_allow_html=True)
            col_m1, col_m2 = st.columns(2)
            with col_m1:
                current_degree = st.selectbox("Completed Undergraduate Degree", ["BSc / B.Tech / B.Eng", "BBA / BBS", "BA", "Other Bachelor's"], index=0, key="ug_deg_type")
                institution = st.text_input("Undergraduate University / Institution Name *", value=existing.get("university") or "", placeholder="e.g. University of Dhaka, BUET, BRAC University, MIT")
                field_of_study = st.text_input("Undergraduate Major / Discipline *", value=existing.get("field_of_study") or "", placeholder="e.g. Computer Science & Engineering")
            with col_m2:
                gpa_val = float(existing.get("gpa") or 3.72)
                gpa = st.number_input("Cumulative Undergraduate GPA (0.0 - 4.0 scale) *", min_value=0.0, max_value=4.0, step=0.01, value=min(max(gpa_val, 0.0), 4.0))
                grad_val = int(existing.get("graduation_year") or 2024)
                graduation_year = st.number_input("Undergraduate Graduation Year *", min_value=current_year - 15, max_value=current_year + 4, step=1, value=grad_val)

            # Master's (MSc) Section for PhD Applicants (Optional)
            if is_phd:
                st.markdown('<div class="ep-field-label" style="font-weight: 700; color: #4F46E5; margin-top: 1.25rem; font-size: 0.95rem;">🎓 Master\'s Degree Background (Optional for PhD Applicants)</div>', unsafe_allow_html=True)
                st.caption("If you completed or are currently pursuing a Master's degree prior to PhD, enter your details below. Leave blank if applying for Direct PhD after Bachelor's.")
                col_p_m1, col_p_m2 = st.columns(2)
                with col_p_m1:
                    msc_deg = st.text_input("Master's Degree Title (Optional)", value=existing.get("msc_degree") or "", placeholder="e.g. MSc in Computer Science & Engineering (or leave blank)")
                    msc_inst = st.text_input("Master's University / Institution (Optional)", value=existing.get("msc_university") or "", placeholder="e.g. American International University Bangladesh (or leave blank)")
                with col_p_m2:
                    msc_gpa_raw = existing.get("msc_gpa") or 0.0
                    msc_gpa = st.number_input("Master's Cumulative GPA (0.0 - 4.0 scale)", min_value=0.0, max_value=4.0, step=0.01, value=min(max(float(msc_gpa_raw), 0.0), 4.0), help="Enter 0.0 if not applicable.")
                    msc_year_val = int(existing.get("msc_year") or min(current_year, 2025))
                    msc_year = st.number_input("Master's Completion Year", min_value=current_year - 15, max_value=current_year + 4, step=1, value=msc_year_val)
                msc_thesis = st.text_input("Master's Thesis Topic / Research Focus (Optional)", value=existing.get("msc_thesis") or "", placeholder="e.g. Deep Multi-Agent Coordination and Distributed Reasoning")
                has_msc = bool(msc_inst.strip() or msc_deg.strip() or (msc_gpa and msc_gpa > 0.0))
            else:
                has_msc = False
                msc_deg, msc_inst, msc_gpa, msc_year, msc_thesis = "", "", None, None, ""

            st.divider()
            st.markdown('<div class="ep-section-title">6. Research Domain & Subject Specialization</div>', unsafe_allow_html=True)
            research_domains = st.multiselect(
                "Primary Subject & Research Domain(s) *",
                options=_merged_options(_COMMON_RESEARCH_DOMAINS, existing.get("research_interests")),
                default=existing.get("research_interests") or ["Artificial Intelligence & Machine Learning", "Computer Vision & Pattern Recognition"],
                accept_new_options=True,
                help="Your target discipline for graduate admissions and advisor matching.",
            )

            st.divider()
            st.markdown('<div class="ep-section-title">7. Work Experience, Research Labs & Internships</div>', unsafe_allow_html=True)
            work_experience = st.text_area(
                "Work & Research Experience (Roles, Labs, Companies, Impact)",
                value=_join_list(existing.get("work_experience")),
                placeholder="e.g. Research Assistant at AI & Vision Lab (2 years); Software Engineer at Tech Corp; Teaching Assistant for Data Structures...",
            )

            st.divider()
            pub_header = "8. Peer-Reviewed Publications & Preprints (Prominent for PhD)" if is_phd else "8. Publications, Preprints or Thesis Projects (Optional for MSc)"
            st.markdown(f'<div class="ep-section-title">{pub_header}</div>', unsafe_allow_html=True)
            st.caption("List papers, conferences/journals (e.g. NeurIPS, CVPR, IEEE Access), arXiv preprints, or thesis project:")
            publications_raw = st.text_area(
                "Publications & Preprints",
                value=_join_list(existing.get("publications")),
                placeholder="e.g. Fast Neural Inference on Edge Devices (IEEE Access 2025); Robust Representations under Occlusion (arXiv:2401.12345)",
            )
            publications_list = _split_list(publications_raw)

            projects_raw = st.text_area(
                "Key Capstone & Research Projects",
                value=_join_list(existing.get("projects")),
                placeholder="e.g. Senior Capstone: Real-time traffic flow prediction using graph neural networks; Autonomous navigation with ROS...",
            )
            achievements = projects_raw

            skills = st.multiselect(
                "Technical Tools & Research Methodologies",
                options=_merged_options(_COMMON_SKILLS, [s for s in (existing.get("skills") or []) if not any(s.lower().startswith(p) for p in ["phone:", "ssc", "hsc", "sat", "gre", "ielts", "toefl", "pte"])]),
                default=[s for s in (existing.get("skills") or ["Python", "PyTorch", "Git", "Linux", "Research Writing"]) if s in _COMMON_SKILLS],
                accept_new_options=True,
            )

        st.write("")
        submitted = st.form_submit_button("Save & Complete Student Profile", use_container_width=True, type="primary")

    if not submitted:
        return None

    # Validation
    errors: list[str] = []
    if not name.strip():
        errors.append("Full Name is required.")
    if not email.strip():
        errors.append("Email Address is required.")
    elif not _EMAIL_RE.match(email.strip()):
        errors.append("Please enter a valid email address.")
    if not phone.strip():
        errors.append("Phone Number is required.")
    if not ssc_school.strip():
        errors.append("Secondary School Name is required.")
    if not hsc_college.strip():
        errors.append("Higher Secondary College / School Name is required.")
    if not field_of_study.strip():
        errors.append("Field of Study / Major is required.")
    if not is_ug and not institution.strip():
        errors.append("University / Institution Name is required.")

    if errors:
        for error in errors:
            st.error(error, icon=":material/warning:")
        return None

    # Construct tagged skills/projects so all attributes persist in DB
    tagged_skills = list(skills)
    tagged_skills.append(f"Phone: {phone.strip()}")
    tagged_skills.append(f"SSC: {ssc_exam_type} · {ssc_group} · {ssc_result.strip()} ({ssc_board}, {ssc_year})")
    tagged_skills.append(f"HSC: {hsc_exam_type} · {hsc_group} · {hsc_result.strip()} ({hsc_board}, {hsc_year})")
    if sat_score.strip() and sat_score.strip().upper() != "N/A":
        tagged_skills.append(f"SAT: {sat_score.strip()}")
    if gre_score.strip() and gre_score.strip().upper() != "N/A":
        tagged_skills.append(f"GRE: {gre_score.strip()}")
    if english_score.strip() and english_score.strip().upper() != "N/A":
        tagged_skills.append(f"English: {english_test_type} - {english_score.strip()}")
    if is_phd and has_msc and msc_inst.strip():
        tagged_skills.append(f"MSc: {msc_deg} · {msc_inst} (GPA {msc_gpa}/4.0, {msc_year})")

    target_degree_name = "Undergraduate" if is_ug else ("Masters" if is_msc else "PhD")
    curr_degree = f"BSc & {msc_deg}" if (is_phd and has_msc and msc_deg) else current_degree
    research_list = research_domains if not is_ug else [field_of_study.strip()]

    return {
        "name": name.strip(),
        "email": email.strip(),
        "academic_level": target_degree_name,
        "current_degree": curr_degree,
        "field_of_study": field_of_study.strip(),
        "university": institution.strip(),
        "gpa": float(gpa),
        "graduation_year": int(graduation_year),
        "target_degree": target_degree_name,
        "target_countries": existing.get("target_countries") or [],
        "research_interests": research_list,
        "skills": tagged_skills,
        "publications": publications_list,
        "projects": _split_list(achievements),
        "work_experience": _split_list(work_experience),
        "preferred_funding": existing.get("preferred_funding") or None,
        # Direct keys for immediate session access
        "phone": phone.strip(),
        "ssc_result": ssc_result.strip(),
        "ssc_school": ssc_school.strip(),
        "ssc_group": ssc_group,
        "ssc_board": ssc_board,
        "ssc_year": int(ssc_year),
        "hsc_result": hsc_result.strip(),
        "hsc_college": hsc_college.strip(),
        "hsc_group": hsc_group,
        "hsc_board": hsc_board,
        "hsc_year": int(hsc_year),
        "sat_score": sat_score.strip(),
        "gre_score": gre_score.strip(),
        "english_score": english_score.strip(),
        "has_msc": has_msc,
        "msc_degree": msc_deg.strip() if has_msc else "",
        "msc_university": msc_inst.strip() if has_msc else "",
        "msc_gpa": float(msc_gpa) if (has_msc and msc_gpa) else None,
        "msc_year": int(msc_year) if (has_msc and msc_year) else None,
        "msc_thesis": msc_thesis.strip() if has_msc else "",
        "is_complete": True,
    }
