import streamlit as st
import psycopg2
import requests
from datetime import datetime

# ------------------------
# Config
# ------------------------
API_BASE = "http://localhost:8000/admin"  # FastAPI endpoint
DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "vector_db",
    "user": "vector_user",
    "password": "vector_pass"
}

# ------------------------
# DB Helper
# ------------------------

def get_connection():
    return psycopg2.connect(
        host="localhost",
        database="vector_db",
        user="vector_user",
        password="vector_pass"
    )
def fetch_files():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT file_id, file_name, domain_name, created_at, status
        FROM file_status
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    conn.close()
    return rows

def fetch_page_count(file_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM playbook_detailed WHERE file_id = %s", (file_id,))
    total_pages = cur.fetchone()[0]
    conn.close()
    return total_pages

def fetch_page_data(file_id, page_num):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT content
        FROM playbook_detailed
        WHERE file_id = %s AND page_no = %s
    """, (file_id, page_num))
    data = cur.fetchone()
    conn.close()
    return data

# ---------------- STREAMLIT UI ----------------
st.set_page_config(page_title="Playbook File Manager", layout="wide")

st.title("📚 Playbook File Manager")
st.subheader("📄 Uploaded Files")

files = fetch_files()

# ---------------- FILE LIST ----------------
for file_id, file_name, domain_name, created_at, status in files:
    col1, col2 = st.columns([6, 2])
    with col1:
        if st.button(f"{file_name} ({domain_name}) - {created_at.strftime('%Y-%m-%d %H:%M:%S')}", key=str(file_id)):
            st.session_state.selected_file = file_id
            st.session_state.current_page = 1
    with col2:
        status_color = "green" if status.lower() == "embedded" else "orange"
        st.markdown(
            f"<div style='text-align:right; color:{status_color}; font-weight:bold;'>{status}</div>",
            unsafe_allow_html=True
        )

# ---------------- PAGE VIEWER ----------------
if "selected_file" in st.session_state:
    file_id = st.session_state.selected_file
    total_pages = fetch_page_count(file_id)

    st.markdown("---")
    st.subheader("📖 File Viewer")

    col_pages, col_content = st.columns([2, 8])

    # LEFT COLUMN → Page Numbers
    with col_pages:
        st.write("**Pages**")
        for p in range(1, total_pages + 1):
            if st.button(str(p), key=f"page_{p}"):
                st.session_state.current_page = p

    # RIGHT COLUMN → Page Content
    with col_content:
        page_num = st.session_state.get("current_page", 1)
        page_data = fetch_page_data(file_id, page_num)
        
        if page_data:
            content = page_data
            st.markdown(f"**content:** {content if content else 'N/A'}")
        else:
            st.warning("No data for this page.")