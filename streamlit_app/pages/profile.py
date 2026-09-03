from __future__ import annotations

import streamlit as st

from api.client import (
    BackendError,
    create_profile,
    delete_document,
    get_profile,
    list_documents,
    update_profile,
    upload_document,
)
from components.common import render_backend_error, section_header
from components.header import render_page_header
from components.profile_card import render_completion_bar
from components.profile_form import render_profile_form
from utils.formatting import profile_completion

_DOCUMENT_TYPES = {
    "CV / Resume": "cv",
    "Transcript": "transcript",
    "Research Proposal": "research_proposal",
    "Previous SOP": "previous_sop",
    "Publication": "publication",
    "Other": "other",
}


def render() -> None:
    render_page_header(
        "My Profile",
        "Keep your academic background and goals up to date -- EduPath AI uses this to find your best-fit opportunities.",
        eyebrow="Profile",
    )

    profile_id = st.session_state.get("profile_id")
    profile = st.session_state.get("profile")

    if profile_id:
        st.caption(f"Editing existing profile · ID: `{profile_id}`")
    else:
        with st.expander("Already have a profile? Load it by ID"):
            existing_id = st.text_input("Profile ID", key="load_profile_id")
            if st.button("Load Profile", icon=":material/download:"):
                _load_profile(existing_id)

    payload = render_profile_form(existing=profile)
    if payload is not None:
        try:
            if profile_id:
                result = update_profile(profile_id, payload)
            else:
                result = create_profile(payload)
        except BackendError as error:
            render_backend_error(error, key="profile-save")
            result = None

        if result is not None:
            st.session_state["profile_id"] = result["id"]
            merged = dict(result)
            merged.update(payload)
            merged["is_complete"] = True
            st.session_state["profile"] = merged
            profile_id = result["id"]

            st.success("Academic Profile saved and verified! All portal features are now unlocked.", icon=":material/verified:")
            completion = profile_completion(merged)
            render_completion_bar(completion)
            st.write("")
            col_l1, col_l2 = st.columns(2)
            with col_l1:
                st.page_link("pages/dashboard.py", label="Go to Command Center →", icon=":material/dashboard:")
            with col_l2:
                st.page_link("pages/counseling.py", label="Calibrate AI Counseling →", icon=":material/auto_awesome:")
            st.rerun()

    if profile_id:
        st.divider()
        _render_documents_section(profile_id)


def _render_documents_section(profile_id: str) -> None:
    section_header(
        "Documents",
        "Upload your CV, transcript, or prior SOP so EduPath AI can ground SOP drafts in your real background.",
    )

    with st.form("document_upload_form", border=True):
        upload_cols = st.columns([2, 1])
        with upload_cols[0]:
            uploaded_file = st.file_uploader("Choose a file", type=["pdf", "txt", "docx"], label_visibility="collapsed")
        with upload_cols[1]:
            doc_type_label = st.selectbox("Type", list(_DOCUMENT_TYPES.keys()), label_visibility="collapsed")
        submitted = st.form_submit_button("Upload", icon=":material/upload_file:", use_container_width=True)

    if submitted:
        if uploaded_file is None:
            st.warning("Choose a file first.", icon=":material/warning:")
        else:
            try:
                upload_document(profile_id, _DOCUMENT_TYPES[doc_type_label], uploaded_file.name, uploaded_file.getvalue())
            except BackendError as error:
                render_backend_error(error, key="document-upload")
            else:
                st.success(f"Uploaded {uploaded_file.name}.", icon=":material/check_circle:")
                st.rerun()

    try:
        documents = list_documents(profile_id)
    except BackendError as error:
        render_backend_error(error, key="document-list")
        return

    if not documents:
        st.caption("No documents uploaded yet.")
        return

    for document in documents:
        with st.container(key=f"document-row-{document['id']}", border=True):
            row = st.columns([3, 2, 1, 1])
            with row[0]:
                st.markdown(f"**{document['filename']}**")
            with row[1]:
                st.caption(document["document_type"].replace("_", " ").title())
            with row[2]:
                st.caption(f"{document['chunk_count']} chunk(s)")
            with row[3]:
                if st.button("Delete", key=f"delete-doc-{document['id']}", icon=":material/delete:"):
                    try:
                        delete_document(document["id"])
                    except BackendError as error:
                        render_backend_error(error, key=f"document-delete-{document['id']}")
                    else:
                        st.rerun()


def _load_profile(profile_id: str) -> None:
    if not profile_id or not profile_id.strip():
        st.warning("Enter a profile ID first.", icon=":material/warning:")
        return
    try:
        result = get_profile(profile_id.strip())
    except BackendError as error:
        render_backend_error(error, key="profile-load")
        return
    st.session_state["profile_id"] = result["id"]
    st.session_state["profile"] = result
    st.success("Profile loaded.", icon=":material/check_circle:")
    st.rerun()


render()
