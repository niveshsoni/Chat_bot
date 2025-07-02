# api.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from QnA_portion.gemini_rag import get_gemini_response
from admin.admin import router as admin_router

app = FastAPI(
    title="Financial QA API",
    docs_url="/admin/docs",  # 👈 this changes the Swagger UI location
    redoc_url=None           # disable ReDoc (optional)
)

class QueryInput(BaseModel):
    question: str

@app.post("/ask") #routing
async def ask_question(query: QueryInput): # it's function
    try:
        result = get_gemini_response(query.question)
        print("datatype of results: ",type(result))
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount admin routes
app.include_router(admin_router, prefix="/admin")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)