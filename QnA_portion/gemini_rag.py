import uuid
from QnA_portion.hybrid_rrf_search import HybridRRFSearch
from langchain_core.prompts import PromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnableSequence
from QnA_portion.db_logger import log_request, get_active_table_names

GOOGLE_API_KEY = "AIzaSyBQIKEIBPWZ_f7SQxJsLXkTnrW5fNcJAVA"

llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.2,
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
    'host': 'localhost',
    'port': 5432
}



chain = prompt_template | llm

def get_gemini_response(question: str) -> dict:
    request_id = str(uuid.uuid4())
    active_tables = get_active_table_names()
    if not active_tables:
        raise Exception("❌ No active table found in onboarding")
    try:
        all_results = []

        # Search across all active tables
        for table in active_tables: 
            searcher = HybridRRFSearch(  # we have created the object here fot the hybridrffsearch (searcher=object)
                db_config=DB_CONFIG,
                table_name=table
                # sql_output_file=f"hybrid_query_debug_{table}.txt"
            )
            results = searcher.ask_question(question)

            # Attach source table (optional for debugging)
            for r in results:
                r["source_table"] = table

            all_results.extend(results)

        print(len(all_results))

        # Sort all results by score
        sorted_results = sorted(all_results, key=lambda x: x["score"], reverse=True)[:5]
        # print("-----------------------------------------------------------------------------------")
        # print("chunks that are passing to llm is: ",sorted_results)
        # print(len(sorted_results))
        # print("-----------------------------------------------------------------------------------")
        # print()
        context_docs = "\n\n".join([r["document"] for r in sorted_results])
        print("---------------------------------------------------------------------------------------")
        print(context_docs)
        print("----------------------------------------------------------------------------------------")


        response = chain.invoke({
            "context": context_docs,
            "question": question
        })

        if response.content.strip() == "ERROR 504: Content not found.":
            log_request(request_id, question, None, "failure", error="Data not found")
            raise Exception("LLM did not return a valid answer.")
        

        else:
            log_request(request_id, question, response.content, "success")
            return {
                "request_id": request_id,
                "question": question,
                "answer": response.content
            }

    except Exception as e:
        print(str(e))
        raise
