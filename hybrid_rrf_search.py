import psycopg2
from pgvector.psycopg2 import register_vector
from sentence_transformers import SentenceTransformer
import json

class HybridRRFSearch:
    def __init__(self, db_config, table_name, model_name='all-MiniLM-L6-v2'):
        self.table_name = table_name
        # self.sql_output_file = sql_output_file
        self.model = SentenceTransformer(model_name)
        self.conn = psycopg2.connect(**db_config)
        self.cursor = self.conn.cursor()
        register_vector(self.conn)

        self.query_template = f"""
        SELECT
            searches.id,
            searches.page_no,
            searches.data,
            searches.document,
            ROUND(100 * public.rrf_score(rank,10) / (1.0 / 11),2) AS score
        FROM (
            (
                SELECT
                    id,
                    page_no,
                    data,
                    document,
                    RANK() OVER (ORDER BY %s::vector <=> embedding) AS rank
                FROM {self.table_name}
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
                    RANK() OVER (ORDER BY ts_rank_cd(to_tsvector(document), plainto_tsquery(%s)) DESC) AS rank
                FROM {self.table_name}
                WHERE plainto_tsquery(%s) @@ to_tsvector(document)
                ORDER BY rank
                LIMIT 5
            )
        ) AS searches
        GROUP BY searches.id, searches.page_no, searches.data, searches.document,rank
        ORDER BY score DESC
        LIMIT 5;
        """

    def ask_question(self, question):
        embedding = self.model.encode(question).tolist()
        embedding_str = f"ARRAY{json.dumps(embedding)}::vector"

    # Prepare a readable version of the query
        readable_query = self.query_template
        readable_query = readable_query.replace("%s::vector", embedding_str, 2)
        readable_query = readable_query.replace("%s", f"'{question}'", 2)

        print("\n✅ Final SQL Query:\n")
        print(readable_query)


        # if self.sql_output_file:
        #     self._save_query_file(question, embedding)

        self.cursor.execute(self.query_template, (embedding, embedding, question, question))
        results = self.cursor.fetchall()

        return [
            {
                'id': row[0],
                'page_no': row[1],
                'data': row[2],
                'document': row[3],
                'score': float(row[4])
            }
            for row in results
        ]

    # def _save_query_file(self, question, embedding):
    #     query_str = self.query_template
    #     query_str = query_str.replace("%s::vector", f"ARRAY{embedding}::vector", 2)
    #     query_str = query_str.replace("%s", f"'{question}'", 2)

    #     with open(self.sql_output_file, "w", encoding="utf-8") as f:
    #         f.write("-- FINAL SQL QUERY (values substituted for terminal use)\n\n")
    #         f.write(query_str)

    #     print(f"✅ Query saved to {self.sql_output_file}")
