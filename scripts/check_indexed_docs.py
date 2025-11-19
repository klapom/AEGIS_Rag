"""Quick script to check what documents are indexed in Qdrant."""

import asyncio
from qdrant_client import AsyncQdrantClient
from collections import defaultdict


async def main():
    # Connect to Qdrant
    client = AsyncQdrantClient(host="localhost", port=6333, prefer_grpc=True)

    try:
        # Get collection info
        collection_info = await client.get_collection("aegis_documents")
        print(f"Total chunks in Qdrant: {collection_info.points_count}\n")

        if collection_info.points_count == 0:
            print("No documents indexed yet!")
            return

        # Scroll through all points
        scroll_result = await client.scroll(
            collection_name="aegis_documents",
            limit=1000,
            with_payload=True,
        )

        # Group by document
        docs = defaultdict(int)
        for point in scroll_result[0]:
            if point.payload and "document_id" in point.payload:
                doc_id = point.payload["document_id"]
                # Extract filename
                if "\\" in doc_id:
                    filename = doc_id.split("\\")[-1]
                elif "/" in doc_id:
                    filename = doc_id.split("/")[-1]
                else:
                    filename = doc_id
                docs[filename] += 1

        print(f"Documents indexed ({len(docs)} unique documents):\n")
        for idx, (filename, chunk_count) in enumerate(sorted(docs.items()), 1):
            print(f"{idx}. {filename} ({chunk_count} chunks)")

    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
