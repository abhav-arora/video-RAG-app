import os
import shutil
import json
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import chromadb
import google.generativeai as genai
from dotenv import load_dotenv
import yt_dlp

# Load environment variables
load_dotenv()

app = FastAPI()

# --- CORS SETUP (Crucial for Vercel) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- GOOGLE GEMINI SETUP ---
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY is missing! Check Render Environment Variables.")

genai.configure(api_key=GOOGLE_API_KEY)

# --- LIGHTWEIGHT DATABASE SETUP ---
# We use a simple persistent storage path
chroma_client = chromadb.PersistentClient(path="./my_knowledge_base")
collection = chroma_client.get_or_create_collection(name="video_rag")

class ChatRequest(BaseModel):
    question: str

@app.get("/")
def home():
    return {"status": "System Ready", "backend": "Lightweight V2"}

def get_gemini_embedding(text):
    """Generates embeddings using Google's Cloud API instead of local RAM."""
    result = genai.embed_content(
        model="models/embedding-001",
        content=text,
        task_type="retrieval_document",
        title="Video Chunk"
    )
    return result['embedding']

@app.post("/process")
def process_video(link: str = Form(...)):
    try:
        # 1. Clear old data to save space
        try:
            chroma_client.delete_collection("video_rag")
            global collection
            collection = chroma_client.get_or_create_collection(name="video_rag")
        except:
            pass

        # 2. Download Captions Only (Skip Audio to save RAM)
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['en'],
            'outtmpl': 'video_subs',
            'quiet': True
        }
        
        transcript_text = ""
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)
            # Check for subtitles
            if 'subtitles' in info and 'en' in info['subtitles']:
                ydl.download([link])
                with open("video_subs.en.vtt", "r", encoding="utf-8") as f:
                    transcript_text = f.read()
            # Check for auto-captions
            elif 'automatic_captions' in info and 'en' in info['automatic_captions']:
                ydl.download([link])
                with open("video_subs.en.vtt", "r", encoding="utf-8") as f:
                    transcript_text = f.read()
            else:
                return {"status": "Error", "message": "No captions found for this video. (Lightweight mode only supports captioned videos)"}

        # 3. Process Text & Create Embeddings
        # Split text into chunks ~1000 chars
        chunks = [transcript_text[i:i+1000] for i in range(0, len(transcript_text), 1000)]
        
        ids = []
        embeddings = []
        documents = []

        for idx, chunk in enumerate(chunks):
            # Use Google API for embedding (0 RAM usage!)
            vector = get_gemini_embedding(chunk)
            
            ids.append(f"id_{idx}")
            embeddings.append(vector)
            documents.append(chunk)

        # 4. Store in Chroma
        collection.add(ids=ids, embeddings=embeddings, documents=documents)

        return {"status": "Processing Complete", "chunks": len(chunks)}

    except Exception as e:
        return {"status": "Error", "message": str(e)}

@app.post("/chat")
def chat(request: ChatRequest):
    try:
        # 1. Convert User Question to Embedding (Google API)
        question_embedding = genai.embed_content(
            model="models/embedding-001",
            content=request.question,
            task_type="retrieval_query"
        )['embedding']

        # 2. Search Database
        results = collection.query(
            query_embeddings=[question_embedding],
            n_results=5
        )
        
        context_text = "\n".join(results['documents'][0])

        # 3. Ask Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        You are a helpful assistant. Answer the question based ONLY on the context below.
        
        Context:
        {context_text}
        
        Question: {request.question}
        """
        
        response = model.generate_content(prompt)
        return {"answer": response.text}

    except Exception as e:
        return {"answer": f"Error: {str(e)}"}