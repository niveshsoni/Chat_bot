import streamlit as st
import requests
import time
from typing import Optional, Dict

# -------------------------------------------------
# Configuration
# -------------------------------------------------
# Change this if your FastAPI backend is hosted elsewhere
BASE_URL = "http://localhost:8000"
UPLOAD_ENDPOINT = f"{BASE_URL}/admin/UPLOAD"
SUBMIT_ENDPOINT = f"{BASE_URL}/admin/submit"
PAGE_ENDPOINT = f"{BASE_URL}/admin/file_view_by_page"

# -------------------------------------------------
# Helper functions
# -------------------------------------------------

def upload_file(file) -> str:
    """Send the file to /admin/UPLOAD and return the file_id."""
    files = {"file": (file.name, file, "text/plain")}
    resp = requests.post(UPLOAD_ENDPOINT, files=files, timeout=120)
    resp.raise_for_status()
    return resp.json()["file_id"]


def trigger_embedding(file_id: str) -> None:
    """Kick off embedding & onboarding via /admin/submit."""
    data = {"file_id": file_id}
    resp = requests.post(SUBMIT_ENDPOINT, data=data, timeout=120)
    resp.raise_for_status()


def fetch_page(file_id: str, page_no: int) -> Optional[Dict]:
    """Query a single page via /admin/file_view_by_page.

    Returns None if the page isn't available yet (404/500)."""
    data = {"file_id": file_id, "page_no": page_no}
    resp = requests.post(PAGE_ENDPOINT, data=data)
    if resp.status_code == 200:
        return resp.json()
    return None


def discover_total_pages(file_id: str, max_probe: int = 200) -> int:
    """Probe sequentially until a page is missing to infer total page count."""
    for i in range(1, max_probe + 1):
        if fetch_page(file_id, i) is None:
            return i - 1
    return max_probe

# -------------------------------------------------
# Streamlit UI layout & styling
# -------------------------------------------------

def inject_css():
    st.markdown(
        """
        <style>
            /* General background */
            .block-container {background-color: #bfbfbf;}
            /* Blue editable inputs */
            textarea, input[type="text"] {
                background-color: #6ec6ff !important;
                color: #000000 !important;
                font-weight: 600;
            }
            /* Buttons */
            .stButton>button {
                background-color: #6ec6ff !important;
                color: black !important;
                font-weight: 600;
                border-radius: 4px;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


# -------------------------------------------------
# App state initialisation (Session State)
# -------------------------------------------------
if "file_id" not in st.session_state:
    st.session_state.file_id = None
if "total_pages" not in st.session_state:
    st.session_state.total_pages = 0
if "current_page" not in st.session_state:
    st.session_state.current_page = 1

# -------------------------------------------------
# Main layout
# -------------------------------------------------
st.set_page_config(layout="wide", page_title="Playbook Admin")
inject_css()

left, right = st.columns([1, 5])

# --------------- Sidebar / left panel ---------------
with left:
    st.header("Upload")
    uploaded_file = st.file_uploader("Choose a .txt file", type=["txt"])
    if uploaded_file is not None:
        if st.button("Submit ✨"):
            with st.spinner("Uploading & parsing..."):
                try:
                    file_id = upload_file(uploaded_file)
                    st.session_state.file_id = file_id
                    st.success(f"Uploaded successfully. File ID: {file_id}")
                    trigger_embedding(file_id)
                    st.info("Embedding started; this may take a minute. Click Refresh below once done.")
                except Exception as e:
                    st.error(f"Upload failed: {e}")

    if st.session_state.file_id:
        if st.button("Refresh ⟳"):
            # Re‑discover pages and redraw UI
            st.session_state.total_pages = discover_total_pages(st.session_state.file_id)
            st.rerun()

        # Display page navigation once pages exist
        if st.session_state.total_pages > 0:
            pages = [f"Page {i}" for i in range(1, st.session_state.total_pages + 1)]
            choice = st.radio("Pages", pages, key="page_selector")
            st.session_state.current_page = int(choice.split()[1])

# --------------- Main editing canvas ---------------
with right:
    st.title("Playbook Page Editor")

    if st.session_state.file_id and st.session_state.total_pages > 0:
        page_no = st.session_state.current_page
        page_data = fetch_page(st.session_state.file_id, page_no)
        if page_data is None:
            st.warning("Page data not ready yet. Try hitting Refresh on the sidebar.")
        else:
            title_val = st.text_input("Title", value=page_data["title"], key="title_input")
            subtitle_val = st.text_input("Subtitle", value=page_data["subtitle"], key="subtitle_input")
            content_val = st.text_area("Content", value=page_data["content"], height=400, key="content_input")

            st.markdown("### ")  # spacer
            if st.button("Save", key="save_button"):
                st.warning("🔧 Save/Update endpoint not yet implemented on the backend.")
    else:
        st.info("Upload a file and click Refresh to begin editing.")

# -------------------------------------------------
# Footer / submit all changes (placeholder)
# -------------------------------------------------
# Position bottom‑right using CSS trick
st.markdown(
    """
    <div style="position: fixed; bottom: 2rem; right: 2rem;">
        <form action="#">
            <button disabled style="padding: 0.75rem 2rem; background: #6ec6ff; border: none; border-radius: 4px; font-weight: 600;">Submit</button>
        </form>
    </div>
    """,
    unsafe_allow_html=True,
)