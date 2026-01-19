from typing import List, Dict, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import pickle
from pathlib import Path


class SemanticSearch:
    """Semantic search engine for code chunks."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize semantic search with embedding model."""
        self.model = SentenceTransformer(model_name)
        self.dimension = 384  # Dimension for all-MiniLM-L6-v2
        self.index = None
        self.chunk_ids = []

    def create_embeddings(self, chunks: List[Dict]) -> List[np.ndarray]:
        """Create embeddings for code chunks."""
        texts = []

        for chunk in chunks:
            # Combine relevant text fields
            text_parts = [
                chunk.get('name', ''),
                chunk.get('signature', ''),
                chunk.get('docstring', ''),
                ' '.join(chunk.get('keywords', [])),
                chunk.get('code', '')[:500]  # First 500 chars of code
            ]
            text = ' '.join(filter(None, text_parts))
            texts.append(text)

        # Generate embeddings
        embeddings = self.model.encode(texts, show_progress_bar=True)
        return embeddings

    def build_index(self, chunks: List[Dict], embeddings: np.ndarray):
        """Build FAISS index for fast similarity search."""
        # Create FAISS index
        self.index = faiss.IndexFlatL2(self.dimension)

        # Add embeddings to index
        self.index.add(embeddings.astype('float32'))

        # Store chunk IDs for retrieval
        self.chunk_ids = [chunk['id'] for chunk in chunks]

        print(f"✅ Built FAISS index with {len(chunks)} chunks")

    def search(self, query: str, top_k: int = 10) -> List[Dict]:
        """Search for relevant code chunks."""
        if self.index is None:
            return []

        # Generate query embedding
        query_embedding = self.model.encode([query])

        # Search in FAISS index
        distances, indices = self.index.search(
            query_embedding.astype('float32'),
            top_k
        )

        # Build results
        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx < len(self.chunk_ids):
                results.append({
                    "chunk_id": self.chunk_ids[idx],
                    "similarity_score": float(1 / (1 + distance)),  # Convert distance to similarity
                    "rank": i + 1
                })

        return results

    def save_index(self, project_id: str, save_dir: str):
        """Save FAISS index and metadata to disk."""
        save_path = Path(save_dir) / project_id
        save_path.mkdir(parents=True, exist_ok=True)

        # Save FAISS index
        faiss.write_index(self.index, str(save_path / "faiss.index"))

        # Save chunk IDs
        with open(save_path / "chunk_ids.pkl", 'wb') as f:
            pickle.dump(self.chunk_ids, f)

        print(f"💾 Saved search index to {save_path}")

    def load_index(self, project_id: str, load_dir: str):
        """Load FAISS index and metadata from disk."""
        load_path = Path(load_dir) / project_id

        if not load_path.exists():
            raise FileNotFoundError(f"Index not found at {load_path}")

        # Load FAISS index
        self.index = faiss.read_index(str(load_path / "faiss.index"))

        # Load chunk IDs
        with open(load_path / "chunk_ids.pkl", 'rb') as f:
            self.chunk_ids = pickle.load(f)

        print(f"📂 Loaded search index from {load_path}")

    def get_similar_chunks(self, chunk_id: str, top_k: int = 5) -> List[str]:
        """Find similar chunks to a given chunk."""
        if chunk_id not in self.chunk_ids:
            return []

        # Get index of chunk
        idx = self.chunk_ids.index(chunk_id)

        # Get embedding
        embedding = self.index.reconstruct(idx).reshape(1, -1)

        # Search for similar
        distances, indices = self.index.search(embedding, top_k + 1)

        # Skip first result (itself)
        similar_ids = [
            self.chunk_ids[i]
            for i in indices[0][1:]
            if i < len(self.chunk_ids)
        ]

        return similar_ids
