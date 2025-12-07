import re
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Configurations
TXT_FILE = r"gastro_playbook.txt"
table_name = "gastro_playbook_22june"
DB_CONFIG = {
    'dbname': 'vector_db',
    'user': 'vector_user',
    'password': 'vector_pass',
    'host': 'postgres',
    'port': 5432
}
MODEL_NAME = 'all-MiniLM-L6-v2' #it convert text into embeddings
EMBEDDING_DIM = 384

# --- Load Model ---
model = SentenceTransformer(MODEL_NAME)

# --- Connect to PostgreSQL ---
conn = psycopg2.connect(**DB_CONFIG)
cursor = conn.cursor()

# Ensure pgvector extension is enabled
cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
conn.commit()

register_vector(conn)

# --- Create Table ---
cursor.execute(f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        id SERIAL PRIMARY KEY,
        page_no INT,
        data TEXT,
        document TEXT,
        embedding VECTOR({EMBEDDING_DIM})
    );
""")
conn.commit()

# --- Parse Pages ---
def parse_pages(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    pages = re.split(r'Page:\s*(\d+)\s*', text)[1:]
    print("**")
    print(pages)
    print("**")
    data = []

    for i in range(0, len(pages), 2):
        page_no = int(pages[i])
        page_text = pages[i+1]

        info_type = re.search(r'Information Type:\s*(.*?)\s*\n', page_text).group(1).strip()
        title = re.search(r'Title:\s*(.*?)\s*\n', page_text).group(1).strip()
        subtitle = re.search(r'SubTitle:\s*(.*?)\s*\n', page_text).group(1).strip()
        content_match = re.search(r'={40,}\s*\n(.*?)\n={40,}', page_text, re.DOTALL)

        if not content_match:
            continue

        content = content_match.group(1).strip()
        metadata = f"Page: {page_no}, Information Type: {info_type}, Title: {title}, SubTitle: {subtitle}"
        document = f"{metadata}\n{content}"

        data.append((page_no, content, document))

    return data

# --- Embed and Store ---
def insert_to_db(records):
    for page_no, content, document in records:
        embedding = model.encode(content).tolist()
        cursor.execute(f"""
            INSERT INTO {table_name} (page_no, data, document, embedding)
            VALUES (%s, %s, %s, %s)
        """, (page_no, content, document, embedding))
    conn.commit()

# --- Run Everything ---
pages = parse_pages(TXT_FILE)
insert_to_db(pages)

print("✅ All pages embedded and stored as single chunks.")