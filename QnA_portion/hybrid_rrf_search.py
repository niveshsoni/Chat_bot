import json
import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer


class HybridRRFSearch:
    """
    Hybrid RRF search on a single file (file_id) combining vector‑similarity
    and full‑text scores, re‑ranked with Reciprocal Rank Fusion.
    """

    def __init__(self, db_config, table_name, file_id, model_name="all-MiniLM-L6-v2"):
        self.file_id = file_id
        self.table_name = table_name

        self.model = SentenceTransformer(model_name)
        self.conn = psycopg2.connect(**db_config)
        self.cursor = self.conn.cursor()
        register_vector(self.conn)

        # ---- SQL template (6 placeholders) ----
        self.query_template = f"""
        SELECT
            searches.id,
            searches.page_no,
            searches.data,
            searches.document,
            ROUND(100 * public.rrf_score(rank, 10) / (1.0 / 11), 2) AS score
        FROM (
            (
                SELECT
                    id,
                    page_no,
                    data,
                    document,
                    RANK() OVER (ORDER BY %s::vector <=> embedding) AS rank
                FROM {self.table_name}
                WHERE file_id = %s
                ORDER BY %s::vector <=> embedding
                LIMIT 5
            )
            UNION ALL
            (
                SELECT
                    id,
                    page_no,
                    data,
                    document,
                    RANK() OVER (
                        ORDER BY ts_rank_cd(
                            to_tsvector(document),
                            plainto_tsquery(%s)
                        ) DESC
                    ) AS rank
                FROM {self.table_name}
                WHERE file_id = %s
                  AND plainto_tsquery(%s) @@ to_tsvector(document)
                ORDER BY rank
                LIMIT 5
            )
        ) AS searches
        GROUP BY searches.id, searches.page_no, searches.data, searches.document, rank
        ORDER BY score DESC
        LIMIT 5;
        """

    # --------------------------------------------------------------------- #
    # Public method
    # --------------------------------------------------------------------- #
    def ask_question(self, question: str):
        """
        Run the hybrid search for a user question and return top‑ranked rows.
        """
        # 1) Build vector
        embedding = self.model.encode(question).tolist()

        # 2) Show a readable query (optional debugging)
        self._print_readable_sql(question, embedding)

        # 3) Execute — supply **all six** positional parameters
        self.cursor.execute(
            self.query_template,
            (
                embedding,          # 1st  %s (ORDER BY similarity)
                self.file_id,       # 2nd  %s
                embedding,          # 3rd  %s (ORDER BY similarity again)
                question,           # 4th  %s (FTS query text)
                self.file_id,       # 5th  %s
                question            # 6th  %s (FTS query text again)
            ),
        )
        rows = self.cursor.fetchall()

        # 4) Transform to Python objects
        return [
            {
                "id": row[0],
                "page_no": row[1],
                "data": row[2],
                "document": row[3],
                "score": float(row[4]),
            }
            for row in rows
        ]

    # --------------------------------------------------------------------- #
    # Helpers
    # --------------------------------------------------------------------- #
    def _print_readable_sql(self, question: str, embedding):
        """
        Replace the two embedding placeholders and the two text placeholders
        so you can copy–paste the query into psql for diagnostics.  Keep the
        file‑ID placeholders literal so the WHERE clauses are still obvious.
        """
        emb_array = f"ARRAY{json.dumps(embedding)}::vector"

        q = self.query_template
        q = q.replace("%s::vector", emb_array, 2)  # both similarity spots
        q = q.replace("%s", f"'{question}'", 2)    # both FTS text spots
        print("\n✅ Final SQL Query (preview):\n")
        print(q)
