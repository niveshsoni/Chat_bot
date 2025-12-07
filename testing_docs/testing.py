import pandas as pd
import requests
import json
import time

# Load Excel with domain_name and question columns
df = pd.read_excel(r"/Users/niveshsoni/Desktop/chatbot/testing_docs/gastro questions.xlsx")  # Replace with your actual Excel filename


# Prepare results list
results = []

url = "http://localhost:8000/ask"
headers = {
    'accept': 'application/json',
    'Content-Type': 'application/json'
}

# Loop through each question
for idx, row in df.iterrows():
    domain = row['Domain']
    question = row['Question']
    
    for i in range(5):  # Send 5 requests per question
        payload = {
            "domain_name": domain,
            "question": question
        }
        try:
            start_time = time.time()
            response = requests.post(url, headers=headers, json=payload)
            end_time = time.time()
            duration = round(end_time - start_time, 4)

            data = response.json()
            results.append({
                "domain_name": domain,
                "question": question,
                "hit_number": i + 1,
                "answer": data.get("answer", ""),
                "chunk_retrieval_sec": data.get("timings", {}).get("chunk_retrieval_sec", None),
                "llm_response_sec": data.get("timings", {}).get("llm_response_sec", None),
                "total_time_taken_sec": duration
            })

        except Exception as e:
            results.append({
                "domain_name": domain,
                "question": question,
                "hit_number": i + 1,
                "answer": str(e),
                "chunk_retrieval_sec": None,
                "llm_response_sec": None,
                "total_time_taken_sec": None
            })

# Convert results to DataFrame and save
results_df = pd.DataFrame(results)
results_df.to_excel("output_5_hits_with_answer_and_timings.xlsx", index=False)
