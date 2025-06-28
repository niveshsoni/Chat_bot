import psycopg2
import json

# Load database config and embedding table from config.json
with open("config.json") as f:
    config = json.load(f)

db_config = config['db_config']
table_name = config['embeddings_table']

def get_connection():
    return psycopg2.connect(
        host=db_config['host'],
        port=db_config['port'],
        database=db_config['database'],
        user=db_config['user'],
        password=db_config['password']
    )

# def setup_onboarding_table():
#     conn = get_connection()
#     cur = conn.cursor()
#     cur.execute("""
#         CREATE TABLE IF NOT EXISTS onboarding (
#             id SERIAL PRIMARY KEY,
#             table_name TEXT UNIQUE,
#             is_active CHAR(1) DEFAULT 'n'
#         )
#     """)
#     conn.commit()
#     cur.execute("SELECT * FROM onboarding WHERE table_name = %s", (table_name,))
#     if not cur.fetchone():
#         cur.execute("INSERT INTO onboarding (table_name, is_active) VALUES (%s, 'y')", (table_name,))
#     conn.commit()
#     cur.close()
#     conn.close()

def get_active_table_names():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT table_name FROM onboarding WHERE is_active = 'y'")
    tables = [row[0] for row in cur.fetchall()]
    print("tables are: ",tables)
    cur.close()
    conn.close()
    return tables

def log_request(request_id, question, answer, status, error=None):
    conn = get_connection()
    cur = conn.cursor()

    # Create table if not exists
    cur.execute("""
        CREATE TABLE IF NOT EXISTS request_logs (
            id SERIAL PRIMARY KEY,
            request_id TEXT,
            question TEXT,
            status TEXT,
            error TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Add answer column if missing
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='request_logs' AND column_name='answer'
            ) THEN
                ALTER TABLE request_logs ADD COLUMN answer TEXT;
            END IF;
        END
        $$;
    """)

    cur.execute("""
        INSERT INTO request_logs (request_id, question, answer, status, error)
        VALUES (%s, %s, %s, %s, %s)
    """, (request_id, question, answer, status, error))

    conn.commit()
    cur.close()
    conn.close()

# Automatically ensure onboarding setup is done
# setup_onboarding_table()
