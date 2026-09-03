"""
Profile Completion Gate Screen.
Displayed when an unverified student attempts to access counseling or advanced features.
"""
import streamlit as st
from components.common import render_html
from components.header import render_page_header

render_page_header(
    "Profile Completion Required",
    "Complete your student academic records to unlock AI Counseling, University Matching & Tracking.",
    eyebrow="Onboarding Gate",
)

render_html(
    """
    <div style="background: #FFFFFF; border: 1.5px solid #C7D2FE; border-radius: 16px; padding: 2rem; max-width: 680px; margin: 1rem auto; box-shadow: 0 10px 25px -5px rgba(99, 102, 241, 0.1);">
        <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1rem;">
            <div style="width: 48px; height: 48px; border-radius: 12px; background: #EEF2FF; display: flex; align-items: center; justify-content: center; font-size: 1.5rem; color: #4F46E5;">
                🔒
            </div>
            <div>
                <div style="font-size: 1.2rem; font-weight: 800; color: #0F172A;">Feature Temporarily Locked</div>
                <div style="font-size: 0.85rem; color: #64748B;">Academic Profile Verification Required</div>
            </div>
        </div>

        <p style="color: #475569; font-size: 0.92rem; line-height: 1.6; margin-bottom: 1.25rem;">
            EduPath AI uses a 7-agent workforce that verifies admission eligibility, faculty alignments, and university cutoff percentiles.
            Before deploying the counseling workforce, we need your foundational academic credentials:
        </p>

        <ul style="color: #334155; font-size: 0.88rem; line-height: 1.8; margin-bottom: 1.5rem; padding-left: 1.25rem;">
            <li><strong>Undergraduate Applicants:</strong> SSC/O-Level, HSC/A-Level groups & results, SAT scores, English test, and ECA.</li>
            <li><strong>Master's & PhD Applicants:</strong> Undergraduate degree, GPA, research domain, GRE, and publications/projects.</li>
        </ul>
    </div>
    """
)

col1, col2, col3 = st.columns([1, 1.8, 1])
with col2:
    if st.button("✦ Complete Academic Profile Now →", type="primary", use_container_width=True, icon=":material/badge:"):
        st.switch_page("pages/profile.py")
