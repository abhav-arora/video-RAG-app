import os
import google.genai as genai
from ingest import process_source 
from db import add_to_db, query_db

## CONFIGURATION
GOOGLE_API_KEY = "AIzaSyBcbIXPjrvfKOazOGW2j9S9HN8jSHlFr3E"

client =  genai.Client(api_key=GOOGLE_API_KEY)

def generate_answer(question, results):
    
    print(" AI is reading the transcripts to formulate an answer...")
    
    # 1. Preparing the context 
    context_text = ""
    timestamps = []
    
    # ChromaDB results structure is a bit nested
    documents = results['documents'][0]
    metadatas = results['metadatas'][0]
    
    for i in range(len(documents)):
        chunk_text = documents[i]
        meta = metadatas[i]
        timestamp = f"[{meta['start']} - {meta['end']}]"
        
        # We feed this into the prompt so the AI knows the facts
        context_text += f"Timestamp {timestamp}: {chunk_text}\n\n"
        timestamps.append(timestamp)

    # 2. The Prompt (The "Instructions")
    prompt = f"""
    You are a helpful teaching assistant. Answer the student's question based ONLY on the provided video transcripts below.
    
    If the answer is not in the transcript, say "I couldn't find that in the video."
    
    QUESTION: {question}
    
    TRANSCRIPT SEGMENTS:
    {context_text}
    
    INSTRUCTIONS:
    - Answer clearly and concisely.
    - Mention the specific timestamps where the information is found.
    """

    # 3. Calling the LLM
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite", 
        contents=prompt
    )
    
    return response.text, timestamps

def main():
    print(" AI Video Tutor (Deep Learning RAG)")
    
    while True:
        print("\n" + "="*40)
        choice = input("Option: (A)dd Video | (S)earch | (Q)uit: ").upper()
        
        if choice == "Q":
            break
            
        elif choice == "A":
            source = input("Enter YouTube Link or File Path: ").strip().replace('"', '')
            video_name = input("Short name for this video: ").strip()
            segments = process_source(source)
            if segments:
                add_to_db(segments, video_name)
                
        elif choice == "S":
            question = input("\n Ask a question: ")
            
            # Step 1: Search the DB (Retrieval)
            results = query_db(question, n_results=5) # Get top 5 matches
            
            # Step 2: Generate Answer (Generation)
            if results['documents'][0]:
                answer, sources = generate_answer(question, results)
                
                print("\n" + "-"*20 + "  AI ANSWER " + "-"*20)
                print(answer)
                print("-" * 50)
            else:
                print(" No relevant parts found in the video index.")

if __name__ == "__main__":
    main()