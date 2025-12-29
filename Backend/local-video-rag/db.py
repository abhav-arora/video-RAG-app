import chromadb
from chromadb.utils import embedding_functions

# 1. Setup the Database (Persistent means it saves to disk)
chroma_client = chromadb.PersistentClient(path="my_knowledge_base")

# 2. Setup the Embedding Model
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# 3. Creating a Collection
collection = chroma_client.get_or_create_collection(
    name="video_rag",
    embedding_function=embedding_func
)

def add_to_db(segments, video_name):
    print(f" Saving {len(segments)} segments to database...")
    
    
    documents = []  
    metadatas = []  
    ids = []       

    for i, seg in enumerate(segments):
        documents.append(seg["text"])
        metadatas.append({
            "video_name": video_name,
            "start": seg["start"],
            "end": seg["end"]
        })
    
        ids.append(f"{video_name}_chunk_{i}")

   
    collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    print(" Saved to Knowledge Base!")

def query_db(question, n_results=3):
    print(f" Searching for: '{question}'...")
    
    results = collection.query(
        query_texts=[question],
        n_results=n_results
    )
    
 
    return results

if __name__ == "__main__":
    # Just a dummy test to see if DB creation works
    print("Testing DB setup...")
    # (We aren't adding anything yet, just checking if imports work)
    print(f"Collection count: {collection.count()}")