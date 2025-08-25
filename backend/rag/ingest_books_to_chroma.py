import os, json, uuid
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

# # -------- Settings --------
SCRIPT_DIR = Path(__file__).resolve().parent
JSON_PATH = SCRIPT_DIR.parent / "data" / "book_summaries.json"    # target file
DB_DIR = SCRIPT_DIR.parent / "chroma_db"  # persisted locally
COLLECTION_NAME = "books"

# -------- Safety checks --------
if not JSON_PATH.exists():
    # Helpful diagnostics
    cwd = Path.cwd()
    raise FileNotFoundError(
        "Could not find the JSON file.\n"
        f"Expected at: {JSON_PATH}\n"
        f"Current working dir: {cwd}\n"
    )

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise EnvironmentError("Please set OPENAI_API_KEY in your environment.")

# -------- Connect to Chroma (persistent) --------
client = chromadb.PersistentClient(path=DB_DIR)

# Use Chroma's built-in OpenAI embedding function helper
openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=api_key,
    model_name="text-embedding-3-small"
)

# Create or get the collection, using cosine distance
collection = client.get_or_create_collection(
    name=COLLECTION_NAME,
    embedding_function=openai_ef,
    metadata={"hnsw:space": "cosine"}  # good default for embeddings
)

# -------- Load your JSON --------
with JSON_PATH.open("r", encoding="utf-8") as f:
    books = json.load(f)

# Basic validation
if not isinstance(books, list):
    raise ValueError("Expected a list of items in the JSON file.")
required_keys = {"title", "summary"}

# -------- Prepare and upsert --------
ids = []
documents = []
metadatas = []

for item in books:
    if not required_keys.issubset(item.keys()):
        raise ValueError(f"Each item must contain keys {required_keys}. Got: {list(item.keys())}")

    # Build a single text field to embed. You can customize this if you want different weighting.
    text = f"Title: {item['title']}\n\nSummary: {item['summary']}"
    documents.append(text)
    metadatas.append({"title": item["title"]})
    ids.append(str(uuid.uuid4()))  # unique IDs

# Upsert in batches (in case you have many items)
BATCH = 64
for i in range(0, len(documents), BATCH):
    collection.upsert(
        ids=ids[i:i+BATCH],
        documents=documents[i:i+BATCH],
        metadatas=metadatas[i:i+BATCH],
    )

print(f"Upserted {len(documents)} items into Chroma collection '{COLLECTION_NAME}' at '{DB_DIR}'.")

# -------- Quick retrieval demo --------
def get_book_recommendations(query, n=3):
    """Retrieve books similar to the given title."""
    results = collection.query(
        query_texts=[query],
        n_results=n,
        include=["documents", "metadatas", "distances"]
    )
    # for doc, meta, dist in zip(results["documents"][0], results["metadatas"][0], results["distances"][0]):
    #     print(f"- {meta['title']}  (distance: {dist:.4f})")
    return results
