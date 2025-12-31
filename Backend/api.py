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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

chroma_client = chromadb.PersistentClient(path="./my_knowledge_base")
collection = chroma_client.get_or_create_collection(name="video_rag")

class ChatRequest(BaseModel):
    question: str

def get_video_id(url):
    if "v=" in url:
        return url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in url:
        return url.split("youtu.be/")[1].split("?")[0]
    return url

@app.get("/")
def home():
    return {"status": "Alive"}

@app.post("/process")
def process_video(link: str = Form(...)):
    try:
        # 1. Clear old data
        try:
            chroma_client.delete_collection("video_rag")
            global collection
            collection = chroma_client.get_or_create_collection(name="video_rag")
        except:
            pass

        # 2. Get ID
        video_id = get_video_id(link)
        
        # 3. SMART TRANSCRIPT FETCHING (The Fix)
        try:
            # Get the list of all available transcripts
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            
            # Logic: Try to find English (Manual or Auto)
            try:
                # First try to find a manually created English transcript
                transcript = transcript_list.find_manually_created_transcript(['en', 'en-US', 'en-GB']).fetch()
            except:
                # If no manual, try to find an auto-generated English transcript
                transcript = transcript_list.find_generated_transcript(['en', 'en-US', 'en-GB']).fetch()
                
        except Exception as e:
            return {"status": "error", "message": "Could not find English captions (Manual or Auto) for this video."}
        
        # 4. Make Text
        full_text = " ".join([t['text'] for t in transcript])
        
        # 5. Save to DB
        chunks = [full_text[i:i+1000] for i in range(0, len(full_text), 1000)]
        
        ids = []
        embeddings = []
        documents = []

        for idx, chunk in enumerate(chunks):
            result = genai.embed_content(
                model="models/embedding-001",
                content=chunk,
                task_type="retrieval_document",
                title="Chunk"
            )
            ids.append(f"id_{idx}")
            embeddings.append(result['embedding'])
            documents.append(chunk)

        collection.add(ids=ids, embeddings=embeddings, documents=documents)

        return {"status": "success", "chunks": len(chunks)}

    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/chat")
def chat(request: ChatRequest):
    try:
        q_embed = genai.embed_content(
            model="models/embedding-001",
            content=request.question,
            task_type="retrieval_query"
        )['embedding']

        results = collection.query(query_embeddings=[q_embed], n_results=5)
        
        if not results['documents']:
             return {"answer": "I haven't watched a video yet."}

        context = "\n".join(results['documents'][0])

        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(f"Context: {context}\n\nQuestion: {request.question}")
        
        return {"answer": response.text}

    except Exception as e:
        return {"answer": "I am having trouble answering right now."}