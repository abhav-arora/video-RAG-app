from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
# Imports for the new Google SDK
from google import genai
from google.genai import types

# Import your local logic
from ingest import process_source
from db import add_to_db, query_db

app = FastAPI()

# --- CORS (Connects React to Python) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURATION ---
# PASTE YOUR KEY HERE
GOOGLE_API_KEY = "AIzaSyBcbIXPjrvfKOazOGW2j9S9HN8jSHlFr3E"


# Initialize the NEW Client
client = genai.Client(api_key=GOOGLE_API_KEY)

# Data Models
class VideoRequest(BaseModel):
    url: str
    name: str

class ChatRequest(BaseModel):
    question: str

@app.post("/process")
def process_video_endpoint(request: VideoRequest):
    print(f"⚡ Processing Video: {request.url}")
    try:
        segments = process_source(request.url)
        if segments:
            add_to_db(segments, request.name)
            return {"status": "success", "chunks": len(segments)}
        else:
            raise HTTPException(status_code=400, detail="Processing returned no segments.")
    except Exception as e:
        print(f"❌ PROCESS ERROR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    print(f"\n💬 Question Received: {request.question}")
    
    try:
        # 1. Search DB
        results = query_db(request.question, n_results=5)
        
        # Check if DB is empty or returned nothing
        if not results or not results['documents'] or not results['documents'][0]:
            print("❌ DB Search returned empty.")
            return {"answer": "I couldn't find any relevant info in the video.", "sources": []}

        # 2. Build Context
        found_docs = results['documents'][0]
        metadatas = results['metadatas'][0]
        context_text = ""
        timestamps = []
        
        for i in range(len(found_docs)):
            timestamp = f"[{metadatas[i]['start']} - {metadatas[i]['end']}]"
            context_text += f"Timestamp {timestamp}: {found_docs[i]}\n\n"
            timestamps.append(timestamp)

        # 3. Generate Answer (Using the NEW SDK Syntax)
        print(" Sending to Gemini...")
        
        prompt = f"""
        You are a helpful assistant. Use the transcript below to answer the question.
        
        TRANSCRIPT:
        {context_text}
        
        QUESTION: {request.question}
        
        INSTRUCTIONS:
        - Answer based ONLY on the transcript.
        - Mention the timestamps (e.g. [00:01:30]) where you found the answer.
        """
        
        # THIS IS THE PART THAT WAS LIKELY CRASHING
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite", 
            contents=prompt
        )
        
        print(" Answer Generated!")
        return {"answer": response.text, "sources": timestamps}

    except Exception as e:
        # This will print the REAL error in your terminal
        print(f" CRITICAL ERROR in /chat: {e}")
        # Return a safe error message to the frontend so it doesn't just crash
        return {
            "answer": f"System Error: {str(e)}. Check terminal for details.", 
            "sources": []
        }

# To run: uvicorn api:app --reload