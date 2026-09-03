from __future__ import annotations

import os
import streamlit as st

from api.client import check_health_cached
from api.exceptions import BackendError
from components.auth import render_logout_button
from components.common import render_html
from utils.formatting import initials


def render_sidebar_logo() -> None:
    """Renders the official brand logo above sidebar navigation."""
    try:
        logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "logo.svg")
        if os.path.exists(logo_path):
            st.logo(logo_path)
    except Exception:
        pass


def render_sidebar_brand() -> None:
    """Legacy hook kept for backwards compatibility."""
    pass


def render_sidebar_footer() -> None:
    """Single unified EduPath AI workspace & student account menu at the bottom of the sidebar."""
    render_sidebar_unified_menu()


def render_sidebar_unified_menu() -> None:
    """Unified EduPath AI workspace + student account menu in a single sleek dark popover card."""
    with st.sidebar:
        user = st.session_state.get("current_user")
        profile = st.session_state.get("profile") or {}

        render_html('<div class="ep-sidebar-divider" style="margin-top: 1rem; margin-bottom: 0.85rem;"></div>')

        if user:
            raw_name = user.get("name") or user.get("email", "Student Account")
            sub = profile.get("target_degree") or profile.get("current_degree") or "PhD Candidate"
            email = user.get("email", "")
            initial = initials(raw_name)
        else:
            raw_name, sub, email, initial = "Guest Student", "Not signed in", "", "?"

        menu_label = f"{raw_name} · EduPath AI"

        with st.popover(menu_label, icon=":material/account_circle:", use_container_width=True):
            # 1. EduPath AI Workspace Header (Dark Theme)
            render_html(
                f"""
                <div style="padding: 0.2rem 0 0.5rem 0;">
                    <div style="display: flex; align-items: center; gap: 0.65rem; margin-bottom: 0.75rem;">
                        <div class="ep-brand-mark" style="width: 34px; height: 34px; font-size: 0.95rem; border-radius: 9px; box-shadow: 0 4px 12px rgba(124, 58, 237, 0.4);">E</div>
                        <div>
                            <div style="font-weight: 800; font-size: 0.95rem; color: #FFFFFF; line-height: 1.2; letter-spacing: -0.01em;">EduPath AI</div>
                            <div style="font-size: 0.7rem; color: #818CF8; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em;">AI Academic Workforce</div>
                        </div>
                    </div>

                    <div style="background: #131C31; border: 1px solid #1E293B; border-radius: 10px; padding: 0.75rem; margin-bottom: 0.75rem;">
                        <div style="display: flex; align-items: center; gap: 0.65rem;">
                            <div class="ep-avatar" style="width: 34px; height: 34px; font-size: 0.82rem;">{initial}</div>
                            <div style="flex: 1; min-width: 0;">
                                <div style="font-weight: 700; font-size: 0.88rem; color: #F1F5F9; line-height: 1.2;">{raw_name}</div>
                                <div style="font-size: 0.72rem; color: #94A3B8; margin-top: 0.15rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{email}</div>
                            </div>
                            <span class="ep-badge indigo" style="font-size: 0.68rem; background: rgba(99, 102, 241, 0.2); border-color: rgba(99, 102, 241, 0.4); color: #C7D2FE;">{sub}</span>
                        </div>
                    </div>
                </div>
                """
            )

            # 2. Account & Workspace Actions
            st.markdown('<div class="ep-menu-section-header">Quick Navigation</div>', unsafe_allow_html=True)
            st.page_link("pages/profile.py", label="Academic Profile & Docs", icon=":material/badge:")
            st.page_link("pages/settings.py", label="AI Settings & Memory", icon=":material/tune:")

            st.divider()

            # 3. System & Session
            _render_backend_status()
            st.write("")
            if user:
                render_logout_button()


def _render_backend_status() -> None:
    try:
        check_health_cached()
        online = True
    except BackendError:
        online = False

    dot_class = "online" if online else "offline"
    text = "AI Core Online" if online else "AI Core Offline"
    port_text = "FastAPI :8000" if online else "Offline"

    render_html(
        f"""
        <div class="ep-sidebar-status-pill" style="background: #131C31 !important; border-color: #1E293B !important;">
            <span class="ep-status-dot {dot_class}"></span>
            <span class="ep-sidebar-status-text" style="color: #E2E8F0 !important;">{text}</span>
            <span style="color: #64748B; font-size: 0.68rem; margin-left: auto;">{port_text}</span>
        </div>
        """
    )
