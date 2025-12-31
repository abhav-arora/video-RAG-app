import os
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
import google.generativeai as genai
from dotenv import load_dotenv
from youtube_transcript_api import YouTubeTranscriptApi

load_dotenv()

app = FastAPI()

# --- CORS SETUP ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIG ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("WARNING: GOOGLE_API_KEY not found")

genai.configure(api_key=GOOGLE_API_KEY)

chroma_client = chromadb.PersistentClient(path="./my_knowledge_base")
collection = chroma_client.get_or_create_collection(name="video_rag")

class ChatRequest(BaseModel):
    question: str

# Helper to get Video ID from URL
def get_video_id(url):
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    return url

@app.get("/")
def home():
    return {"status": "System Ready", "backend": "Stealth Mode V3"}

@app.post("/process")
def process_video(link: str = Form(...)):
    try:
        # 1. Clean DB
        try:
            chroma_client.delete_collection("video_rag")
            global collection
            collection = chroma_client.get_or_create_collection(name="video_rag")
        except:
            pass

        # 2. Extract Video ID
        video_id = get_video_id(link)
        
        # 3. Get Transcript (Stealth Mode)
        # This bypasses the "Sign in" block by fetching just text
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Combine text
        full_text = " ".join([item['text'] for item in transcript_list])

        # 4. Create Embeddings (Google)
        # Split into 1000 char chunks
        chunks = [full_text[i:i+1000] for i in range(0, len(full_text), 1000)]
        
        ids = []
        embeddings = []
        documents = []

        for idx, chunk in enumerate(chunks):
            result = genai.embed_content(
                model="models/embedding-001",
                content=chunk,
                task_type="retrieval_document",
                title="Video Chunk"
            )
            ids.append(f"id_{idx}")
            embeddings.append(result['embedding'])
            documents.append(chunk)

        collection.add(ids=ids, embeddings=embeddings, documents=documents)

        return {"status": "success", "chunks": len(chunks)}

    except Exception as e:
        print(f"ERROR: {str(e)}")
        # Return success=False so frontend knows it failed
        return {"status": "error", "message": str(e)}

@app.post("/chat")
def chat(request: ChatRequest):
    try:
        question_embedding = genai.embed_content(
            model="models/embedding-001",
            content=request.question,
            task_type="retrieval_query"
        )['embedding']

        results = collection.query(
            query_embeddings=[question_embedding],
            n_results=5
        )
        
        context_text = "\n".join(results['documents'][0])

        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Answer based on this video transcript:
        {context_text}
        
        Question: {request.question}
        """
        
        response = model.generate_content(prompt)
        return {"answer": response.text}

    except Exception as e:
        return {"answer": f"Error: {str(e)}"}