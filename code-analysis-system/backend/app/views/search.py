from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from pathlib import Path

from app.database import get_db
from app.views.deps import get_current_active_user
from app.models.user import User
from app.models.project import Project
from app.models.code_chunk import CodeChunk
from app.services.semantic_search import SemanticSearch

router = APIRouter(prefix="/api/v1/search", tags=["search"])


# Request/Response Models
class SearchRequest(BaseModel):
    query: str
    project_id: str
    top_k: int = 10


class SearchResultItem(BaseModel):
    chunk_id: str
    file_path: str
    chunk_type: str
    name: str
    signature: str
    start_line: int
    end_line: int
    code: str
    docstring: Optional[str]
    similarity_score: float
    rank: int


class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]
    total_results: int


class SimilarChunksResponse(BaseModel):
    chunk_id: str
    similar_chunks: List[SearchResultItem]


@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(
        request: SearchRequest,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Perform semantic search across code chunks."""

    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == request.project_id,
        Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status != "completed":
        raise HTTPException(
            status_code=400,
            detail="Project analysis not completed yet"
        )

    # Load search index
    search_engine = SemanticSearch()
    index_dir = Path(f"backend/app/projects/search_indices")

    try:
        search_engine.load_index(request.project_id, str(index_dir))
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail="Search index not found. Please rerun analysis."
        )

    # Perform search
    search_results = search_engine.search(request.query, request.top_k)

    # Fetch chunk details from database
    chunk_ids = [r["chunk_id"] for r in search_results]
    chunks = db.query(CodeChunk).filter(CodeChunk.id.in_(chunk_ids)).all()

    # Create lookup dictionary
    chunk_dict = {c.id: c for c in chunks}

    # Build response
    results = []
    for search_result in search_results:
        chunk_id = search_result["chunk_id"]
        if chunk_id in chunk_dict:
            chunk = chunk_dict[chunk_id]
            results.append(
                SearchResultItem(
                    chunk_id=chunk.id,
                    file_path=chunk.file_path,
                    chunk_type=chunk.chunk_type,
                    name=chunk.name,
                    signature=chunk.signature,
                    start_line=chunk.start_line,
                    end_line=chunk.end_line,
                    code=chunk.code,
                    docstring=chunk.docstring,
                    similarity_score=search_result["similarity_score"],
                    rank=search_result["rank"]
                )
            )

    return SearchResponse(
        query=request.query,
        results=results,
        total_results=len(results)
    )


@router.get("/similar/{chunk_id}", response_model=SimilarChunksResponse)
async def find_similar_chunks(
        chunk_id: str,
        project_id: str = Query(...),
        top_k: int = 5,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Find similar code chunks to a given chunk."""

    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Verify chunk exists
    chunk = db.query(CodeChunk).filter(CodeChunk.id == chunk_id).first()
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")

    # Load search index
    search_engine = SemanticSearch()
    index_dir = Path(f"backend/app/projects/search_indices")

    try:
        search_engine.load_index(project_id, str(index_dir))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Search index not found")

    # Find similar chunks
    similar_ids = search_engine.get_similar_chunks(chunk_id, top_k)

    # Fetch from database
    similar_chunks = db.query(CodeChunk).filter(
        CodeChunk.id.in_(similar_ids)
    ).all()

    results = [
        SearchResultItem(
            chunk_id=c.id,
            file_path=c.file_path,
            chunk_type=c.chunk_type,
            name=c.name,
            signature=c.signature,
            start_line=c.start_line,
            end_line=c.end_line,
            code=c.code,
            docstring=c.docstring,
            similarity_score=0.9,  # Placeholder
            rank=i + 1
        )
        for i, c in enumerate(similar_chunks)
    ]

    return SimilarChunksResponse(
        chunk_id=chunk_id,
        similar_chunks=results
    )


@router.get("/keywords/{project_id}")
async def get_common_keywords(
        project_id: str,
        top_n: int = 20,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
):
    """Get most common keywords across all chunks in a project."""

    # Verify project ownership
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == current_user.id
    ).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all chunks
    chunks = db.query(CodeChunk).filter(
        CodeChunk.project_id == project_id
    ).all()

    # Count keywords
    keyword_counts = {}
    for chunk in chunks:
        for keyword in (chunk.keywords or []):
            keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

    # Sort and return top N
    top_keywords = sorted(
        keyword_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:top_n]

    return {
        "project_id": project_id,
        "keywords": [
            {"keyword": kw, "count": count}
            for kw, count in top_keywords
        ]
    }
