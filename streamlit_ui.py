import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"  # Adjust if deployed elsewhere

st.set_page_config(page_title="Financial QA Portal", layout="wide")
st.title("📄 Financial QA Portal")

# Sidebar navigation
menu = st.sidebar.radio("📚 Navigate", ["Upload & Embed File", "Onboard Table", "Ask a Question"])

# 1. Upload File & Create Chunk Table
if menu == "Upload & Embed File":
    st.header("📥 Upload and Embed Document")

    uploaded_file = st.file_uploader("📄 Upload a `.txt` file", type=['txt'])
    table_name = st.text_input("📝 Enter table name")

    if st.button("🚀 Create Chunk Table"):
        if uploaded_file and table_name:
            files = {"file": uploaded_file}
            data = {"table_name": table_name}

            with st.spinner("🔄 Embedding document and creating table..."):
                try:
                    response = requests.post(f"{API_URL}/admin/create_chunk_table", files=files, data=data)
                    st.success(response.json()["message"])
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("⚠️ Please upload a file and provide a table name.")

# 2. Onboard Table
elif menu == "Onboard Table":
    st.header("✅ Onboard Existing Table")

    table_name = st.text_input("📌 Enter table name to onboard")

    if st.button("📤 Onboard Table"):
        if table_name:
            with st.spinner("🔄 Onboarding table..."):
                try:
                    response = requests.post(f"{API_URL}/admin/onboard_table", data={"table_name": table_name})
                    st.success(response.json()["message"])
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("⚠️ Please enter a table name.")

# 3. Ask a Question
elif menu == "Ask a Question":
    st.header("💬 Ask a Question from Embedded Knowledge")

    question = st.text_area("❓ Enter your question below:")

    if st.button("🤖 Get Answer"):
        if question:
            with st.spinner("⏳ Getting answer from Gemini..."):
                try:
                    response = requests.post(f"{API_URL}/ask", json={"question": question})
                    result = response.json()
                    print(result)

                    if "answer" in result:
                        st.markdown("### ✅ Bot Response")
                        st.write(result["answer"])

                        if "request_id" in result:
                            st.caption(f"🆔 Request ID: `{result['request_id']}`")

                    elif "detail" in result:
                        st.error(f"❌ {result['detail']}")
                    else:
                        st.error("⚠️ Unknown error occurred.")
                except Exception as e:
                    st.error(f"❌ Exception: {str(e)}")
        else:
            st.warning("⚠️ Please enter a question.")
