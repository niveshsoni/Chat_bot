import uuid
from QnA_portion.hybrid_rrf_search import HybridRRFSearch
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnableSequence
from QnA_portion.db_logger import log_request, get_active_table_names
import time

GOOGLE_API_KEY = "AIzaSyAZcsNCrZBDPylvfh9qvV9_ZX5h7_wBUu8"

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.0,
    google_api_key=GOOGLE_API_KEY
)

prompt_template = PromptTemplate.from_template("""
You are a strict assistant. Use only the context below to answer the question.

### INSTRUCTIONS:
- Return only content from the context, grouped by the title it appears under.
- If answer is from multiple chunks then you should search in all the chunks and respond.   
- if user ask two questions then if one question's response is available and second's not then you will have to respond for that question that's answer is available in context and for second one return "Answer is not available in context". 
- if user ask two questions and response for both question is available in chunks. then you need to specify what are talking about.                                                                                                                                        
- For each page where content is relevant, show:
  Title: <title>\n
  <exact matching content from that page>
- If the answer is not found in the context, return exactly:
  ERROR 504: Content not found.

---

Context:
{context}

---

Question:
{question}

### Output:
""")

DB_CONFIG = {
    'dbname': 'vector_db',
    'user': 'vector_user',
    'password': 'vector_pass',
    'host': 'postgres',
    'port': 5432
}



chain = prompt_template | llm

def get_gemini_response(question: str, domain_name: str) -> dict:
    request_id = str(uuid.uuid4())
    active_playbooks = get_active_table_names(domain_name)
    if not active_playbooks:
        raise Exception("❌ No active playbook found in onboarding")

    try:
        all_results = []

        # ⏱️ Start Chunk Retrieval Timer
        start_chunk = time.time()

        for file_id in active_playbooks:
            searcher = HybridRRFSearch(
                db_config=DB_CONFIG,
                table_name="playbook_vector_table",
                file_id=file_id
            )
            results = searcher.ask_question(question)
            all_results.extend(results)

        # ⏱️ End Chunk Retrieval Timer
        end_chunk = time.time()
        chunk_time = round(end_chunk - start_chunk, 4)

        sorted_results = sorted(all_results, key=lambda x: x["score"], reverse=True)[:5]
        context_docs = "\n\n".join([r["document"] for r in sorted_results])

        # ⏱️ Start LLM Timer
        start_llm = time.time()

        response = chain.invoke({
            "context": context_docs,
            "question": question
        })

        # ⏱️ End LLM Timer
        end_llm = time.time()
        llm_time = round(end_llm - start_llm, 4)

        if response.content.strip() == "ERROR 504: Content not found.":
            log_request(request_id, question, None, "failure",chunk_time,llm_time, error="Data not found")
            raise Exception("LLM did not return a valid answer.")

        else:
            log_request(request_id, question, response.content, "success",chunk_time,llm_time)
            return {
                "request_id": request_id,
                "question": question,
                "answer": response.content,
                "timings": {
                    "chunk_retrieval_sec": chunk_time,
                    "llm_response_sec": llm_time
                }
            }

    except Exception as e:
        print(str(e))
        raise
