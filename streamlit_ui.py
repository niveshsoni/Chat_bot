# import streamlit as st
# import requests
# import time
# from typing import Optional, Dict

# # -------------------------------------------------
# # Configuration
# # -------------------------------------------------
# # Change this if your FastAPI backend is hosted elsewhere
# BASE_URL = "http://localhost:8000"
# UPLOAD_ENDPOINT = f"{BASE_URL}/admin/UPLOAD"
# SUBMIT_ENDPOINT = f"{BASE_URL}/admin/submit"
# PAGE_ENDPOINT = f"{BASE_URL}/admin/file_view_by_page"

# # -------------------------------------------------
# # Helper functions
# # -------------------------------------------------

# def upload_file(file) -> str:
#     """Send the file to /admin/UPLOAD and return the file_id."""
#     files = {"file": (file.name, file, "text/plain")}
#     resp = requests.post(UPLOAD_ENDPOINT, files=files, timeout=120)
#     resp.raise_for_status()
#     return resp.json()["file_id"]


# def trigger_embedding(file_id: str) -> None:
#     """Kick off embedding & onboarding via /admin/submit."""
#     data = {"file_id": file_id}
#     resp = requests.post(SUBMIT_ENDPOINT, data=data, timeout=120)
#     resp.raise_for_status()


# def fetch_page(file_id: str, page_no: int) -> Optional[Dict]:
#     """Query a single page via /admin/file_view_by_page.

#     Returns None if the page isn't available yet (404/500)."""
#     data = {"file_id": file_id, "page_no": page_no}
#     resp = requests.post(PAGE_ENDPOINT, data=data)
#     if resp.status_code == 200:
#         return resp.json()
#     return None


# def discover_total_pages(file_id: str, max_probe: int = 200) -> int:
#     """Probe sequentially until a page is missing to infer total page count."""
#     for i in range(1, max_probe + 1):
#         if fetch_page(file_id, i) is None:
#             return i - 1
#     return max_probe

# # -------------------------------------------------
# # Streamlit UI layout & styling
# # -------------------------------------------------

# def inject_css():
#     st.markdown(
#         """
#         <style>
#             /* General background */
#             .block-container {background-color: #bfbfbf;}
#             /* Blue editable inputs */
#             textarea, input[type="text"] {
#                 background-color: #6ec6ff !important;
#                 color: #000000 !important;
#                 font-weight: 600;
#             }
#             /* Buttons */
#             .stButton>button {
#                 background-color: #6ec6ff !important;
#                 color: black !important;
#                 font-weight: 600;
#                 border-radius: 4px;
#             }
#         </style>
#         """,
#         unsafe_allow_html=True,
#     )


# # -------------------------------------------------
# # App state initialisation (Session State)
# # -------------------------------------------------
# if "file_id" not in st.session_state:
#     st.session_state.file_id = None
# if "total_pages" not in st.session_state:
#     st.session_state.total_pages = 0
# if "current_page" not in st.session_state:
#     st.session_state.current_page = 1

# # -------------------------------------------------
# # Main layout
# # -------------------------------------------------
# st.set_page_config(layout="wide", page_title="Playbook Admin")
# inject_css()

# left, right = st.columns([1, 5])

# # --------------- Sidebar / left panel ---------------
# with left:
#     st.header("Upload")
#     uploaded_file = st.file_uploader("Choose a .txt file", type=["txt"])
#     if uploaded_file is not None:
#         if st.button("Submit ✨"):
#             with st.spinner("Uploading & parsing..."):
#                 try:
#                     file_id = upload_file(uploaded_file)
#                     st.session_state.file_id = file_id
#                     st.success(f"Uploaded successfully. File ID: {file_id}")
#                     trigger_embedding(file_id)
#                     st.info("Embedding started; this may take a minute. Click Refresh below once done.")
#                 except Exception as e:
#                     st.error(f"Upload failed: {e}")

#     if st.session_state.file_id:
#         if st.button("Refresh ⟳"):
#             # Re‑discover pages and redraw UI
#             st.session_state.total_pages = discover_total_pages(st.session_state.file_id)
#             st.rerun()

#         # Display page navigation once pages exist
#         if st.session_state.total_pages > 0:
#             pages = [f"Page {i}" for i in range(1, st.session_state.total_pages + 1)]
#             choice = st.radio("Pages", pages, key="page_selector")
#             st.session_state.current_page = int(choice.split()[1])

# # --------------- Main editing canvas ---------------
# with right:
#     st.title("Playbook Page Editor")

#     if st.session_state.file_id and st.session_state.total_pages > 0:
#         page_no = st.session_state.current_page
#         page_data = fetch_page(st.session_state.file_id, page_no)
#         if page_data is None:
#             st.warning("Page data not ready yet. Try hitting Refresh on the sidebar.")
#         else:
#             title_val = st.text_input("Title", value=page_data["title"], key="title_input")
#             subtitle_val = st.text_input("Subtitle", value=page_data["subtitle"], key="subtitle_input")
#             content_val = st.text_area("Content", value=page_data["content"], height=400, key="content_input")

#             st.markdown("### ")  # spacer
#             if st.button("Save", key="save_button"):
#                 st.warning("🔧 Save/Update endpoint not yet implemented on the backend.")
#     else:
#         st.info("Upload a file and click Refresh to begin editing.")

# # -------------------------------------------------
# # Footer / submit all changes (placeholder)
# # -------------------------------------------------
# # Position bottom‑right using CSS trick
# st.markdown(
#     """
#     <div style="position: fixed; bottom: 2rem; right: 2rem;">
#         <form action="#">
#             <button disabled style="padding: 0.75rem 2rem; background: #6ec6ff; border: none; border-radius: 4px; font-weight: 600;">Submit</button>
#         </form>
#     </div>
#     """,
#     unsafe_allow_html=True,
# )

import os
import requests
import streamlit as st
from typing import Optional

# -----------------------------------------------------------------------------
# Config helpers
# -----------------------------------------------------------------------------

def get_base_url() -> str:
    return st.session_state.get("base_url", "http://localhost:8000")


def set_base_url(url: str):
    st.session_state["base_url"] = url.rstrip("/")


# -----------------------------------------------------------------------------
# Small helpers that wrap HTTP requests + error handling
# -----------------------------------------------------------------------------

def _post(path: str, **kwargs):
    url = f"{get_base_url()}{path}"
    try:
        resp = requests.post(url, **kwargs, timeout=90)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        st.error(f"❌ Request to {url} failed: {exc}")
        return None


# -----------------------------------------------------------------------------
# UI layout
# -----------------------------------------------------------------------------

st.set_page_config(page_title="Playbook QA", layout="centered")

# Force white/light background regardless of user theme
st.markdown(
    """
    <style>
        body, .stApp { background:#ffffff !important; }
        .css-18e3th9 { background:#ffffff !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("🔧 Backend config")
    backend_url = st.text_input("FastAPI base URL", value=get_base_url())
    set_base_url(backend_url)
    st.markdown("---")

# Tabs = high‑level workflow steps ------------------------------------------------

tabs = st.tabs(["1️⃣ Upload", "2️⃣ Embed & onboard", "3️⃣ Browse pages", "4️⃣ Ask" ])

# 1. Upload ---------------------------------------------------------------------
with tabs[0]:
    st.subheader("Step 1 – Upload playbook text file")
    upload_file = st.file_uploader("Choose .txt playbook", type=["txt"])
    if st.button("🚀 Upload") and upload_file is not None:
        with st.spinner("Uploading …"):
            files = {"file": (upload_file.name, upload_file.getvalue(), "text/plain")}
            json = _post("/admin/UPLOAD", files=files)
            if json:
                st.success(f"Uploaded OK – file_id: {json['file_id']}")
                st.session_state["file_id"] = json["file_id"]

# 2. Embed & onboard -------------------------------------------------------------
with tabs[1]:
    st.subheader("Step 2 – Embed & activate playbook")
    file_id = st.text_input("file_id", value=st.session_state.get("file_id", ""))
    if st.button("🔄 Submit for embedding") and file_id:
        with st.spinner("Embedding queued …"):
            data = {"file_id": file_id}
            json = _post("/admin/submit", data=data)
            if json:
                st.success("Embedding job accepted ✔️ – wait until status=embedded in DB.")

# 3. Browse pages ----------------------------------------------------------------
with tabs[2]:
    st.subheader("Step 3 – View parsed page")
    file_id_browse = st.text_input("file_id to browse", value=st.session_state.get("file_id", ""), key="browse_id")
    page_no = st.number_input("Page number", min_value=1, step=1, format="%d")
    if st.button("📖 Fetch page") and file_id_browse:
        with st.spinner("Fetching …"):
            data = {"file_id": file_id_browse, "page_no": int(page_no)}
            json = _post("/admin/file_view_by_page", data=data)
            if json:
                st.markdown(f"### {json['title']}")
                st.markdown(f"**{json['subtitle']}**")
                st.markdown("---")
                st.markdown(json["content"], unsafe_allow_html=True)

# 4. Ask questions ---------------------------------------------------------------
with tabs[3]:
    st.subheader("Step 4 – Ask a question about the active playbook")
    user_q = st.text_area("Your question")
    if st.button("💬 Ask") and user_q:
        with st.spinner("Thinking …"):
            payload = {"question": user_q}
            json = _post("/ask", json=payload)
            if json:
                # get_gemini_response returns whatever you coded; assume str or dict
                st.write(json if isinstance(json, str) else json)


# -----------------------------------------------------------------------------
# Footer
# -----------------------------------------------------------------------------

st.markdown("---")
st.caption("© 2025 Your Company – Streamlit UI for the Financial Playbook QA system")
