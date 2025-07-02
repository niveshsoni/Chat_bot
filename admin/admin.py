import os
import re
import uuid
import psycopg2
from fastapi import APIRouter, UploadFile, Form, HTTPException
from sentence_transformers import SentenceTransformer
from pgvector.psycopg2 import register_vector
from QnA_portion.db_logger import get_connection
from tempfile import NamedTemporaryFile

router = APIRouter()
MODEL_NAME = 'all-MiniLM-L6-v2'
EMBEDDING_DIM = 384
model = SentenceTransformer(MODEL_NAME)

@router.post("/create_chunk_table")
async def create_chunk_table(file: UploadFile, table_name: str = Form(...)):
    try:
        temp_file = NamedTemporaryFile(delete=False, suffix=".txt")
        contents = await file.read()
        temp_file.write(contents)
        temp_file.close()

        records = parse_pages(temp_file.name)
        # print("records are: ")
        # print(records)

        conn = get_connection()
        cur = conn.cursor()
        register_vector(conn)
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                page_no INT,
                data TEXT,
                document TEXT,
                embedding VECTOR({EMBEDDING_DIM})
            );
        """)

        for page_no, content, document in records:
            embedding = model.encode(content).tolist()
            cur.execute(f"""
                INSERT INTO {table_name} (page_no, data, document, embedding)
                VALUES (%s, %s, %s, %s)
            """, (page_no, content, document, embedding))

        conn.commit()
        cur.close()
        conn.close()
        os.remove(temp_file.name)

        return {"message": f"✅ Table '{table_name}' created and embedded successfully."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/onboard_table")
def onboard_table(table_name: str = Form(...)):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS onboarding (
                id SERIAL PRIMARY KEY,
                table_name TEXT UNIQUE,
                is_active CHAR(1) DEFAULT 'n'
            )
        """)
        conn.commit()

        cur.execute("UPDATE onboarding SET is_active = 'n'")
        cur.execute("""
            INSERT INTO onboarding (table_name, is_active)
            VALUES (%s, 'y')
            ON CONFLICT (table_name)
            DO UPDATE SET is_active = 'y'
        """, (table_name,))
        conn.commit()

        cur.close()
        conn.close()

        return {"message": f"✅ Table '{table_name}' onboarded as active."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def parse_pages(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    pages = re.split(r'Page:\s*(\d+)\s*', text)[1:]
    data = []

    for i in range(0, len(pages), 2):
        page_no = int(pages[i])
        page_text = pages[i + 1]

        info_type = re.search(r'Information Type:\s*(.*?)\s*\n', page_text)
        title = re.search(r'Title:\s*(.*?)\s*\n', page_text)
        subtitle = re.search(r'SubTitle:\s*(.*?)\s*\n', page_text)
        content_match = re.search(r'={40,}\s*\n(.*?)\n={40,}', page_text, re.DOTALL)
        print(content_match)

        if not (info_type and title and subtitle and content_match):
            continue

        content = content_match.group(1).strip()
        # print("content is: ",content)
        metadata = f"Page: {page_no}, Information Type: {info_type.group(1).strip()}, Title: {title.group(1).strip()}, SubTitle: {subtitle.group(1).strip()}"
        document = f"{metadata}\n{content}"

        data.append((page_no, content, document))

    return data