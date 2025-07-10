# import os
# import re
# import uuid
# import psycopg2
# from fastapi import APIRouter, UploadFile, Form, HTTPException
# from sentence_transformers import SentenceTransformer
# from pgvector.psycopg2 import register_vector
# from QnA_portion.db_logger import get_connection
# from tempfile import NamedTemporaryFile

# router = APIRouter()
# MODEL_NAME = 'all-MiniLM-L6-v2'
# EMBEDDING_DIM = 384
# model = SentenceTransformer(MODEL_NAME)

# @router.post("/create_chunk_table")
# async def create_chunk_table(file: UploadFile, table_name: str = Form(...)):
#     try:
#         temp_file = NamedTemporaryFile(delete=False, suffix=".txt")
#         contents = await file.read()
#         temp_file.write(contents)
#         temp_file.close()

#         records = parse_pages(temp_file.name)
#         # print("records are: ")
#         # print(records)

#         conn = get_connection()
#         cur = conn.cursor()
#         register_vector(conn)
#         cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
#         cur.execute(f"""
#             CREATE TABLE IF NOT EXISTS {table_name} (
#                 id SERIAL PRIMARY KEY,
#                 page_no INT,
#                 data TEXT,
#                 document TEXT,
#                 embedding VECTOR({EMBEDDING_DIM})
#             );
#         """)

#         for page_no, content, document in records:
#             embedding = model.encode(content).tolist()
#             cur.execute(f"""
#                 INSERT INTO {table_name} (page_no, data, document, embedding)
#                 VALUES (%s, %s, %s, %s)
#             """, (page_no, content, document, embedding))

#         conn.commit()
#         cur.close()
#         conn.close()
#         os.remove(temp_file.name)

#         return {"message": f"✅ Table '{table_name}' created and embedded successfully."}

#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# @router.post("/onboard_table")
# def onboard_table(table_name: str = Form(...)):
#     try:
#         conn = get_connection()
#         cur = conn.cursor()

#         cur.execute("""
#             CREATE TABLE IF NOT EXISTS onboarding (
#                 id SERIAL PRIMARY KEY,
#                 table_name TEXT UNIQUE,
#                 is_active CHAR(1) DEFAULT 'n'
#             )
#         """)
#         conn.commit()

#         cur.execute("UPDATE onboarding SET is_active = 'n'")
#         cur.execute("""
#             INSERT INTO onboarding (table_name, is_active)
#             VALUES (%s, 'y')
#             ON CONFLICT (table_name)
#             DO UPDATE SET is_active = 'y'
#         """, (table_name,))
#         conn.commit()

#         cur.close()
#         conn.close()

#         return {"message": f"✅ Table '{table_name}' onboarded as active."}
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

# def parse_pages(file_path):
#     with open(file_path, 'r', encoding='utf-8') as f:
#         text = f.read()

#     pages = re.split(r'Page:\s*(\d+)\s*', text)[1:]
#     data = []

#     for i in range(0, len(pages), 2):
#         page_no = int(pages[i])
#         page_text = pages[i + 1]

#         info_type = re.search(r'Information Type:\s*(.*?)\s*\n', page_text)
#         title = re.search(r'Title:\s*(.*?)\s*\n', page_text)
#         subtitle = re.search(r'SubTitle:\s*(.*?)\s*\n', page_text)
#         content_match = re.search(r'={40,}\s*\n(.*?)\n={40,}', page_text, re.DOTALL)
#         print(content_match)

#         if not (info_type and title and subtitle and content_match):
#             continue

#         content = content_match.group(1).strip()
#         # print("content is: ",content)
#         metadata = f"Page: {page_no}, Information Type: {info_type.group(1).strip()}, Title: {title.group(1).strip()}, SubTitle: {subtitle.group(1).strip()}"
#         document = f"{metadata}\n{content}"

#         data.append((page_no, content, document))

#     return data

import os
import re
import uuid
import logging
from datetime import datetime
from tempfile import NamedTemporaryFile
from typing import List, Tuple
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Form, HTTPException, UploadFile
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer

from QnA_portion.db_logger import get_connection

# ----------------------------------------------------------------------------
# Config & logging
# ----------------------------------------------------------------------------

logger = logging.getLogger("playbook_router")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())

router = APIRouter()

# ----------------------------------------------------------------------------
# Embedding model (load once)
# ----------------------------------------------------------------------------

model = SentenceTransformer("all-MiniLM-L6-v2")
EMBEDDING_DIM = model.get_sentence_embedding_dimension()

def encode(text: str):
    """Return a float list embedding for text."""
    return model.encode(text).tolist()

# ----------------------------------------------------------------------------
# Database bootstrapping
# ----------------------------------------------------------------------------

def _ensure_file_status_constraint(cur):
    """Ensure status CHECK list is up‑to‑date."""
    cur.execute(
        """
        DO $$
        DECLARE
            _cname text := 'file_status_status_check';
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname=_cname AND conrelid='file_status'::regclass
            ) THEN
                EXECUTE format('ALTER TABLE file_status DROP CONSTRAINT %I', _cname);
            END IF;
        END $$;
        """
    )
    cur.execute(
        """
        ALTER TABLE file_status
        ADD CONSTRAINT file_status_status_check
        CHECK (status IN ('uploaded','processing','new','embedded','failed'));
        """
    )

def _ensure_onboarding_table(cur):
    """Create onboarding table if missing."""
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS onboarding (
            id SERIAL PRIMARY KEY,
            table_name TEXT UNIQUE,
            file_id UUID,
            is_active CHAR(1) DEFAULT 'n'
        );
        """
    )

def create_tables() -> None:
    conn = get_connection()
    cur = conn.cursor()
    register_vector(conn)
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS file_status (
            file_id UUID PRIMARY KEY,
            file_name TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            status TEXT NOT NULL
        );
        """
    )
    _ensure_file_status_constraint(cur)

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS playbook_detailed (
            id SERIAL PRIMARY KEY,
            page_no INT NOT NULL,
            content TEXT NOT NULL,
            document TEXT NOT NULL,
            metadata TEXT NOT NULL,
            file_id UUID REFERENCES file_status(file_id),
            created_at TIMESTAMP NOT NULL
        );
        """
    )

    _ensure_onboarding_table(cur)

    cur.execute(
        f"""
        CREATE TABLE IF NOT EXISTS playbook_vector_table (
            id SERIAL PRIMARY KEY,
            page_no INT,
            data TEXT,
            file_id UUID,
            document TEXT,
            embedding VECTOR({EMBEDDING_DIM})
        );
        """
    )

    conn.commit()
    cur.close()
    conn.close()

# ----------------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------------

@router.post("/UPLOAD")
async def upload(file: UploadFile, background_tasks: BackgroundTasks):
    """Upload a raw text file and queue page splitting."""
    try:
        tmp = NamedTemporaryFile(delete=False, suffix=".txt")
        tmp.write(await file.read())
        tmp.close()

        file_id = uuid.uuid4()
        created_at = datetime.utcnow()

        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO file_status (file_id,file_name,created_at,status)
                   VALUES (%s,%s,%s,%s)""",
            (str(file_id), file.filename, created_at, "uploaded"),
        )
        conn.commit()
        cur.close()
        conn.close()

        background_tasks.add_task(_process_and_store_pages, tmp.name, file_id, created_at)
        return {"file_id": str(file_id), "message": "✅ Upload received. Parsing started."}

    except Exception as exc:
        logger.exception("UPLOAD failed")
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/submit")
async def submit_file(file_id: UUID = Form(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    """Queue embedding + onboarding for a previously uploaded file."""
    background_tasks.add_task(_embed_and_onboard, file_id)
    return {"file_id": str(file_id), "message": "✅ Embedding job queued."}

# ----------------------------------------------------------------------------
# Background tasks
# ----------------------------------------------------------------------------

def _process_and_store_pages(tmp_path: str, file_id: UUID, created_at: datetime) -> None:
    conn = get_connection()
    cur = conn.cursor()
    register_vector(conn)
    try:
        cur.execute("UPDATE file_status SET status='processing' WHERE file_id=%s", (str(file_id),))

        pages = parse_pages(tmp_path)
        for page_no, content, document, metadata in pages:
            cur.execute(
                """INSERT INTO playbook_detailed (page_no,content,document,metadata,file_id,created_at)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                (page_no, content, document, metadata, str(file_id), created_at),
            )
        cur.execute("UPDATE file_status SET status='new' WHERE file_id=%s", (str(file_id),))
        conn.commit()
        logger.info("Pages stored for %s", file_id)
    except Exception as exc:
        conn.rollback()
        cur.execute("UPDATE file_status SET status='failed' WHERE file_id=%s", (str(file_id),))
        conn.commit()
        logger.exception("Page extraction failed for %s", file_id)
    finally:
        cur.close()
        conn.close()
        os.remove(tmp_path)


def _embed_and_onboard(file_id: UUID) -> None:
    """Insert embeddings into fixed table and onboard it."""
    conn = get_connection()
    cur = conn.cursor()
    register_vector(conn)

    table_name = "playbook_vector_table"

    try:
        cur.execute("SELECT page_no,content,document FROM playbook_detailed WHERE file_id=%s ORDER BY page_no", (str(file_id),))
        records = cur.fetchall()
        if not records:
            raise ValueError(f"No page data for {file_id}")

        cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        cur.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                page_no INT,
                data TEXT,
                file_id UUID,
                document TEXT,
                embedding VECTOR({EMBEDDING_DIM})
            );
            """
        )
        conn.commit()

        insert_q = f"INSERT INTO {table_name} (page_no,data,file_id,document,embedding) VALUES (%s,%s,%s,%s,%s)"
        for page_no, content, document in records:
            cur.execute(insert_q, (page_no, content, str(file_id), document, encode(content)))
        cur.execute("UPDATE file_status SET status='embedded' WHERE file_id=%s", (str(file_id),))

        _onboard_table(cur, table_name, file_id)
        conn.commit()
        logger.info("Vector table %s ready and onboarded", table_name)
    except Exception as exc:
        conn.rollback()
        cur.execute("UPDATE file_status SET status='failed' WHERE file_id=%s", (str(file_id),))
        conn.commit()
        logger.exception("Embedding/onboarding failed for %s", file_id)
    finally:
        cur.close()
        conn.close()

# ----------------------------------------------------------------------------
# Utils
# ----------------------------------------------------------------------------

#----------------------------------------------------------------------------
#file_view_by_page api
#----------------------------------------------------------------------------

@router.post("/file_view_by_page")
async def submit_file(file_id: UUID = Form(...), page_no: int = Form(...)):
    conn = get_connection()
    cur = conn.cursor()
    register_vector(conn) 
    cur.execute("SELECT page_no, content, metadata FROM playbook_detailed WHERE file_id = %s AND page_no = %s",
    (str(file_id), int(page_no)))
    records = cur.fetchall()
    print("records are:  ")
    print("-----------------------")
    for record in records:
        page_no = page_no
        page_content = record[1]
        metadata = dict(item.split(":", 1) for item in record[2].split(",") if ":" in item)
        metadata = {k.strip(): v.strip() for k, v in metadata.items()}
        title = metadata.get("Title")
        subtitle = metadata.get("SubTitle")


        print("Title:", title)
        print("Subtitle:", subtitle)
        
        
    if not records:
        raise ValueError(f"No page data for {file_id}")
  
    
    return {"page_no": page_no, "content": page_content, "title": title, "subtitle": subtitle}


def parse_pages(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    pages = re.split(r'Page:\s*(\d+)\s*', text)[1:]
    data = []

    for i in range(0, len(pages), 2):
        page_no = int(pages[i])
        page_text = pages[i + 1]

        lines = page_text.strip().splitlines()
        info_type = title = subtitle = None
        content_lines = []
        in_content = False

        for line in lines:
            line = line.strip()

            if line.startswith("Information Type:"):
                info_type = line[len("Information Type:"):].strip()
            elif line.startswith("Title:"):
                title = line[len("Title:"):].strip()
                print("%%%",title)
            elif line.startswith("SubTitle:"):
                subtitle = line[len("SubTitle:"):].strip()
                print("!!!",subtitle)
            elif "====" in line:
                if not in_content:
                    in_content = True  # Start capturing content
                    continue
                else:
                    break  # End of content block
            elif in_content:
                content_lines.append(line)

        if not (info_type and title and subtitle is not None and content_lines):
            continue

        content = "\n".join(content_lines).strip()
        metadata = f"Page: {page_no}, Information Type: {info_type}, Title: {title}, SubTitle: {subtitle}"
        document = f"{metadata}\n{content}"
        data.append((page_no, content, document, metadata))

    return data

def _onboard_table(cur, table_name: str, file_id: UUID):
    _ensure_onboarding_table(cur)
    cur.execute("UPDATE onboarding SET is_active='n' WHERE is_active='y'")
    cur.execute(
        """INSERT INTO onboarding (table_name,file_id,is_active)
               VALUES (%s,%s,'y')
               ON CONFLICT (table_name) DO UPDATE SET is_active='y',file_id=EXCLUDED.file_id""",
        (table_name, str(file_id))
    )

