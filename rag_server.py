"""
rag_server.py
Pathway Document Store server — indexes fraud policy documents in real time
and serves semantic search via REST API at http://localhost:8765

The Streamlit app retrieves relevant policy chunks from here,
then passes them to OpenAI to answer user questions (RAG pattern).
"""
import os
import pathway as pw
from pathway.xpacks.llm.document_store import DocumentStore
from pathway.xpacks.llm.embedders import OpenAIEmbedder
from pathway.xpacks.llm.splitters import TokenCountSplitter
from pathway.xpacks.llm.servers import DocumentStoreServer

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

if not OPENAI_API_KEY:
    raise ValueError(
        "OPENAI_API_KEY environment variable is not set. "
        "Please set it in your .env file or export it."
    )

print("[RAG Server] Indexing fraud policy documents...")
print("[RAG Server] Watching ./data/policies/ for new/updated documents...")

# 1. Read policy documents as a live stream
policy_docs = pw.io.fs.read(
    "./data/policies/",
    format="binary",
    mode="streaming",
    with_metadata=True,
)

# 2. Configure embedder and splitter
embedder = OpenAIEmbedder(
    api_key=OPENAI_API_KEY,
    model="text-embedding-3-small",
)

splitter = TokenCountSplitter(max_tokens=300)

# 3. Build the live Document Store (auto-syncs when files change)
store = DocumentStore(
    [policy_docs],
    embedder=embedder,
    splitter=splitter,
)

# 4. Serve via REST API
# Endpoints available:
#   POST /v1/retrieve  — semantic search
#   GET  /v1/statistics — index stats
server = DocumentStoreServer(
    host="0.0.0.0",
    port=8765,
    document_store=store,
)

print("[RAG Server] Starting server at http://0.0.0.0:8765")
print("[RAG Server] Query endpoint: POST http://localhost:8765/v1/retrieve")
server.run()
