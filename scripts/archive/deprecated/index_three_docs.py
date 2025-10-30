"""
Index specific three documents for Sprint 19 UI testing.
Uses BGE-M3 embeddings (1024 dimensions).
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from llama_index.core import SimpleDirectoryReader, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.ollama import OllamaEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient, models


async def main():
    print("[*] Starting document indexing for 3 specific documents...")

    # Configuration
    collection_name = "aegis_documents"
    embedding_model = "bge-m3"
    vector_dim = 1024

    # Specific files to index
    base_path = project_root / "data" / "sample_documents" / "3. Basic Scripting"
    files_to_index = [
        base_path / "DE-D-OTAutBasic.pdf",
        base_path / "DE-D-OTAutAdvanced.pdf",
    ]

    # Step 1: Initialize Qdrant Client
    print(f"\n[1/6] Connecting to Qdrant...")
    qdrant_client = QdrantClient(url="http://localhost:6333")

    # Check if collection exists, delete if it does
    try:
        collections = qdrant_client.get_collections().collections
        if any(c.name == collection_name for c in collections):
            print(f"   Deleting existing collection '{collection_name}'...")
            qdrant_client.delete_collection(collection_name)
    except Exception as e:
        print(f"   Warning: {e}")

    # Create collection with BGE-M3 dimensions
    print(f"   Creating collection '{collection_name}' with {vector_dim} dimensions...")
    qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config=models.VectorParams(
            size=vector_dim,
            distance=models.Distance.COSINE,
        ),
    )
    print("   [OK] Collection created")

    # Step 2: Initialize Embedding Model (BGE-M3)
    print(f"\n[2/6] Initializing embedding model '{embedding_model}'...")
    embed_model = OllamaEmbedding(
        model_name=embedding_model,
        base_url="http://localhost:11434",
    )
    Settings.embed_model = embed_model
    print("   [OK] Embedding model ready")

    # Step 3: Load Specific Documents
    print(f"\n[3/6] Loading specific documents...")
    documents = []
    for file_path in files_to_index:
        if file_path.exists():
            print(f"   Loading: {file_path.name}")
            reader = SimpleDirectoryReader(input_files=[str(file_path)])
            docs = reader.load_data()
            documents.extend(docs)
        else:
            print(f"   WARNING: File not found: {file_path}")

    print(f"   [OK] Loaded {len(documents)} documents")

    # Step 4: Chunk Documents
    print(f"\n[4/6] Chunking documents...")
    splitter = SentenceSplitter(
        chunk_size=512,
        chunk_overlap=128,
    )
    nodes = splitter.get_nodes_from_documents(documents)
    print(f"   [OK] Created {len(nodes)} chunks")

    # Step 5: Create Vector Store and Index
    print(f"\n[5/6] Generating embeddings and indexing...")
    vector_store = QdrantVectorStore(
        client=qdrant_client,
        collection_name=collection_name,
    )

    # Index nodes (this generates embeddings and stores in Qdrant)
    from llama_index.core import VectorStoreIndex, StorageContext

    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context,
        show_progress=True,
    )

    print(f"   [OK] Indexed {len(nodes)} chunks")

    # Step 6: Verify
    print(f"\n[6/6] Verifying indexing...")
    collection_info = qdrant_client.get_collection(collection_name)
    print(f"   Collection '{collection_name}' has {collection_info.points_count} points")

    print("\n[SUCCESS] Indexing complete!")
    print(f"\nSummary:")
    print(f"   - Documents loaded: {len(documents)}")
    print(f"   - Chunks created: {len(nodes)}")
    print(f"   - Points indexed: {collection_info.points_count}")
    print(f"   - Collection: {collection_name}")
    print(f"   - Embedding model: {embedding_model} ({vector_dim}D)")
    print(f"\nIndexed files:")
    for file_path in files_to_index:
        print(f"   - {file_path.name}")


if __name__ == "__main__":
    asyncio.run(main())
