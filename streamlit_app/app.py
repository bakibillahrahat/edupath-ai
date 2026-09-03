from __future__ import annotations

from pathlib import Path

import streamlit as st

# Ensure page config is set as the very first command
st.set_page_config(
    page_title="EduPath AI – Your AI-Powered Path to Studying Abroad",
    page_icon=":material/school:",
    layout="wide",
    initial_sidebar_state="expanded",
)

from components.auth import ensure_current_user, handle_oauth_redirect, render_login_gate, require_auth
from components.sidebar import render_sidebar_footer, render_sidebar_logo
from utils.profile_guard import is_profile_complete
from utils.session import init_session_state


def _load_css() -> None:
    css_path = Path(__file__).resolve().parent / "styles" / "main.css"
    if css_path.exists():
        st.markdown(f"<style>{css_path.read_text()}</style>", unsafe_allow_html=True)


def main() -> None:
    init_session_state()
    _load_css()
    handle_oauth_redirect()

    is_authenticated = ensure_current_user()

    if not is_authenticated:
        page = st.query_params.get("page", "landing")

        if page == "login":
            render_login_gate()
        else:
            nav = st.navigation(
                {
                    "": [
                        st.Page("pages/landing.py", title="Home", icon=":material/home:", default=True, url_path=""),
                    ],
                }
            )
            nav.run()
        return

    require_auth()
    render_sidebar_logo()

    profile = st.session_state.get("profile")
    profile_done = is_profile_complete(profile)

    if not profile_done:
        nav = st.navigation(
            {
                "Onboarding Gate": [
                    st.Page(
                        "pages/profile.py",
                        title="Complete Academic Profile",
                        icon=":material/badge:",
                        default=True,
                        url_path="profile",
                    ),
                ],
                "Locked Features (Complete Profile First)": [
                    st.Page(
                        "pages/profile_gate.py",
                        title="Dashboard (Locked 🔒)",
                        icon=":material/lock:",
                        url_path="dashboard-locked",
                    ),
                    st.Page(
                        "pages/profile_gate.py",
                        title="AI Counseling (Locked 🔒)",
                        icon=":material/lock:",
                        url_path="counseling-locked",
                    ),
                    st.Page(
                        "pages/profile_gate.py",
                        title="Admissions Tracker (Locked 🔒)",
                        icon=":material/lock:",
                        url_path="tracker-locked",
                    ),
                ],
            }
        )
    else:
        nav = st.navigation(
            {
                "Workspace": [
                    st.Page(
                        "pages/dashboard.py",
                        title="Dashboard",
                        icon=":material/dashboard:",
                        default=True,
                        url_path="dashboard",
                    ),
                    st.Page(
                        "pages/discover.py",
                        title="Opportunities & Saved",
                        icon=":material/school:",
                        url_path="opportunities",
                    ),
                ],
                "Applications": [
                    st.Page(
                        "pages/sop.py",
                        title="Document Studio (SOP)",
                        icon=":material/edit_note:",
                        url_path="documents",
                    ),
                    st.Page(
                        "pages/tracker.py",
                        title="Application Tracker",
                        icon=":material/checklist:",
                        url_path="tracker",
                    ),
                ],
                "Account & System": [
                    st.Page(
                        "pages/profile.py",
                        title="Academic Profile & Docs",
                        icon=":material/badge:",
                        url_path="profile",
                    ),
                    st.Page(
                        "pages/settings.py",
                        title="AI Settings & Memory",
                        icon=":material/tune:",
                        url_path="settings",
                    ),
                ],
            }
        )

    render_sidebar_footer()
    nav.run()


if __name__ == "__main__":
    main()
