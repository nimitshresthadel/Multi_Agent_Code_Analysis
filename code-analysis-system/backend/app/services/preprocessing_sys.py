from pathlib import Path
from typing import Dict, List
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from app.services.repo_analyser import RepositoryAnalyzer
from app.services.file_processor import FileProcessor
from app.services.code_chunker import CodeChunker
from app.services.semantic_search import SemanticSearch
from app.models.repo_metadata import RepositoryMetadata
from app.models.file_metadata import FileMetadata
from app.models.code_chunk import CodeChunk
from app.services.progress_tracker import ProgressTracker  # ← ADD
from app.models.progress import ProgressStage, ActivityType


class PreprocessingOrchestrator:
    """Orchestrates the entire preprocessing pipeline."""

    def __init__(self, project_id: str, project_path: str, db: Session):
        self.project_id = project_id
        self.project_path = Path(project_path)
        self.db = db

        # Initialize services
        self.analyzer = RepositoryAnalyzer(str(project_path))
        self.processor = FileProcessor(str(project_path))
        self.chunker = CodeChunker(str(project_path))
        self.search = SemanticSearch()
        self.progress = ProgressTracker(project_id, db)

    def run_full_pipeline(self) -> Dict:
        """Run the complete preprocessing pipeline."""
        print(f"\n{'=' * 60}")
        print(f"🚀 Starting preprocessing for project: {self.project_id}")
        print(f"{'=' * 60}\n")

        results = {
            "project_id": self.project_id,
            "status": "processing",
            "steps": {}
        }

        try:
            # Step 1: Repository Intelligence
            print("📊 Step 1: Repository Intelligence")
            repo_metadata = self._run_repository_analysis()
            results["steps"]["repository_analysis"] = {
                "status": "completed",
                "repository_type": repo_metadata.repository_type,
                "confidence": repo_metadata.confidence_score
            }

            # Step 2: File Processing
            print("\n📁 Step 2: File Processing")
            file_metadata = self._run_file_processing()
            results["steps"]["file_processing"] = {
                "status": "completed",
                "total_files": len(file_metadata),
                "files_to_process": len([f for f in file_metadata if not f.should_skip])
            }

            # Step 3: Code Chunking
            print("\n🧩 Step 3: Code Chunking")
            code_chunks = self._run_code_chunking(file_metadata)
            results["steps"]["code_chunking"] = {
                "status": "completed",
                "total_chunks": len(code_chunks)
            }

            # Step 4: Semantic Indexing
            print("\n🔍 Step 4: Semantic Indexing")
            self._run_semantic_indexing(code_chunks)
            results["steps"]["semantic_indexing"] = {
                "status": "completed",
                "indexed_chunks": len(code_chunks)
            }

            self.progress.complete_processing()

            results["status"] = "completed"
            print(f"\n{'=' * 60}")
            print(f"✅ Preprocessing completed successfully!")
            print(f"{'=' * 60}\n")

        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            self.progress.mark_failed(str(e))
            print(f"\n❌ Preprocessing failed: {str(e)}")
            raise

        return results

    def _run_repository_analysis(self) -> RepositoryMetadata:
        """Run repository analysis and save to database."""
        # Analyze repository
        analysis_results = self.analyzer.analyze()

        self.progress.add_info(
            f"Detected {analysis_results['framework']} project ({analysis_results['primary_language']})",
            details=f"Confidence: {analysis_results['confidence_score']:.0%}"
        )

        # Create metadata record
        repo_metadata = RepositoryMetadata(
            id=str(uuid.uuid4()),
            project_id=self.project_id,
            repository_type=analysis_results["repository_type"],
            primary_language=analysis_results["primary_language"],
            framework=analysis_results["framework"],
            entry_points=analysis_results["entry_points"],
            important_files=analysis_results["important_files"],
            config_files=analysis_results["config_files"],
            total_files=analysis_results["total_files"],
            code_files=analysis_results["code_files"],
            total_lines=analysis_results["total_lines"],
            dependencies=analysis_results["dependencies"],
            tech_stack=analysis_results["tech_stack"],
            endpoints_count=analysis_results["endpoints_count"],
            endpoints=analysis_results["endpoints"],
            database_type=analysis_results["database_type"],
            orm_detected=analysis_results["orm_detected"],
            has_tests=analysis_results["has_tests"],
            test_framework=analysis_results["test_framework"],
            confidence_score=analysis_results["confidence_score"],
            analysis_notes=analysis_results["analysis_notes"]
        )

        # Save to database
        self.db.add(repo_metadata)
        self.db.commit()

        # Print summary
        print(f"   ✓ Detected: {repo_metadata.framework} ({repo_metadata.primary_language})")
        print(f"   ✓ Entry points: {len(repo_metadata.entry_points)}")
        print(f"   ✓ Total files: {repo_metadata.total_files}")
        print(f"   ✓ Code files: {repo_metadata.code_files}")
        print(f"   ✓ Lines of code: {repo_metadata.total_lines:,}")
        print(f"   ✓ API endpoints: {repo_metadata.endpoints_count}")
        print(f"   ✓ Confidence: {repo_metadata.confidence_score:.0%}")

        # if repo_metadata.tech_stack:
        #     self.progress.add_info(
        #         f"Tech stack: {', '.join(repo_metadata.tech_stack[:5])}"
        #     )

        return repo_metadata

    def _run_file_processing(self) -> List[FileMetadata]:
        """Process files and save metadata to database."""
        # Get all files
        file_list = [str(f.relative_to(self.project_path))
                     for f in self.project_path.rglob('*') if f.is_file()]

        # Process files
        processed_files = self.processor.process_all_files(file_list)

        total_to_process = len(processed_files["process"])

        # Start file processing stage
        self.progress.start_stage(ProgressStage.FILE_PROCESSING, total_to_process)

        file_metadata_list = []
        processed_count = 0

        # Process files marked for processing
        for file_info in processed_files["process"]:
            processed_count += 1
            detailed_metadata = self.processor.extract_file_metadata(file_info["file_path"])

            file_metadata = FileMetadata(
                id=str(uuid.uuid4()),
                project_id=self.project_id,
                file_path=file_info["file_path"],
                file_name=file_info["file_name"],
                file_extension=file_info["file_extension"],
                file_size=file_info["file_size"],
                file_type=file_info.get("file_type", "source"),
                language=file_info.get("language"),
                priority_level=file_info.get("priority_level", 5),
                lines_of_code=detailed_metadata.get("lines_of_code", 0),
                has_classes=detailed_metadata.get("has_classes", False),
                has_functions=detailed_metadata.get("has_functions", False),
                complexity_score=detailed_metadata.get("complexity_score", 0.0),
                imports=detailed_metadata.get("imports", []),
                is_processed=False,
                should_skip=False
            )

            self.db.add(file_metadata)
            file_metadata_list.append(file_metadata)

            # Update progress
            self.progress.update_file_progress(
                file_info["file_name"],
                file_info["file_path"],
                processed_count,
                total_to_process
            )

        # Handle files to skip
        for file_info in processed_files["skip"]:
            file_metadata = FileMetadata(
                id=str(uuid.uuid4()),
                project_id=self.project_id,
                file_path=file_info["file_path"],
                file_name=file_info["file_name"],
                file_extension=file_info["file_extension"],
                file_size=file_info["file_size"],
                should_skip=True,
                skip_reason=file_info.get("skip_reason", "unknown")
            )
            self.db.add(file_metadata)

        self.db.commit()

        self.progress.complete_stage(ProgressStage.FILE_PROCESSING)

        print(f"   ✓ Files to process: {len(processed_files['process'])}")
        print(f"   ✓ Files skipped: {len(processed_files['skip'])}")
        print(f"   ✓ Config files: {len(processed_files['config'])}")
        print(f"   ✓ Test files: {len(processed_files['test'])}")

        if len(processed_files["skip"]) > 10:
            self.progress.add_info(
                f"Skipped {len(processed_files['skip'])} binary/generated files"
            )

        return file_metadata_list

    def _run_code_chunking(self, file_metadata_list: List[FileMetadata]) -> List[CodeChunk]:
        """Chunk code files and save to database."""
        all_chunks = []

        # Sort by priority for processing
        sorted_files = sorted(
            file_metadata_list,
            key=lambda x: x.priority_level,
            reverse=True
        )

        self.progress.start_stage(ProgressStage.CODE_CHUNKING, len(sorted_files))

        all_chunks = []
        files_processed = 0

        for file_meta in sorted_files:
            if file_meta.should_skip or not file_meta.language:
                continue

            files_processed += 1

            # Chunk the file
            chunks = self.chunker.chunk_file(file_meta.file_path, file_meta.language)

            for chunk_data in chunks:
                code_chunk = CodeChunk(
                    id=chunk_data["id"],
                    project_id=self.project_id,
                    file_id=file_meta.id,
                    file_path=chunk_data["file_path"],
                    start_line=chunk_data["start_line"],
                    end_line=chunk_data["end_line"],
                    chunk_type=chunk_data["chunk_type"],
                    name=chunk_data["name"],
                    signature=chunk_data["signature"],
                    code=chunk_data["code"],
                    docstring=chunk_data.get("docstring"),
                    parent_class=chunk_data.get("parent_class"),
                    parameters=chunk_data.get("parameters"),
                    return_type=chunk_data.get("return_type"),
                    calls_functions=chunk_data.get("calls_functions", []),
                    complexity=chunk_data.get("complexity", 1),
                    token_count=chunk_data.get("token_count", 0),
                    keywords=chunk_data.get("keywords", [])
                )

                self.db.add(code_chunk)
                all_chunks.append(code_chunk)

            # Mark file as processed
            file_meta.is_processed = True

            self.progress.update_chunk_progress(
                file_meta.file_name,
                len(chunks)
            )

        self.db.commit()

        self.progress.complete_stage(ProgressStage.CODE_CHUNKING)

        # Print statistics
        chunk_types = {}
        for chunk in all_chunks:
            chunk_types[chunk.chunk_type] = chunk_types.get(chunk.chunk_type, 0) + 1

        print(f"   ✓ Total chunks created: {len(all_chunks)}")
        for chunk_type, count in sorted(chunk_types.items()):
            print(f"      - {chunk_type}: {count}")

        self.progress.add_info(
            f"Created {len(all_chunks)} code chunks",
            details=f"Functions: {chunk_types.get('function', 0)}, Classes: {chunk_types.get('class', 0)}"
        )

        return all_chunks

    def _run_semantic_indexing(self, code_chunks: List[CodeChunk]):
        """Create semantic embeddings and build search index."""
        if not code_chunks:
            print("   ⚠️  No chunks to index")
            return

        self.progress.start_stage(ProgressStage.SEMANTIC_INDEXING)

        # Prepare chunks for embedding
        chunk_dicts = []
        for chunk in code_chunks:
            chunk_dicts.append({
                'id': chunk.id,
                'name': chunk.name,
                'signature': chunk.signature,
                'docstring': chunk.docstring or '',
                'keywords': chunk.keywords or [],
                'code': chunk.code
            })

        # Create embeddings
        print("   ⏳ Generating embeddings...")

        self.progress.add_info("Generating semantic embeddings for code understanding...")

        embeddings = self.search.create_embeddings(chunk_dicts)

        # Build search index
        print("   ⏳ Building search index...")

        self.progress.add_info("Building search index for intelligent code navigation...")
        self.search.build_index(chunk_dicts, embeddings)

        # Save index to disk
        index_dir = self.project_path.parent / "search_indices"
        self.search.save_index(self.project_id, str(index_dir))

        # Store embedding IDs in database
        for i, chunk in enumerate(code_chunks):
            chunk.embedding_id = f"{self.project_id}:{i}"

        self.db.commit()
        self.progress.complete_stage(ProgressStage.SEMANTIC_INDEXING)

        print(f"   ✓ Created {len(embeddings)} embeddings")
        print(f"   ✓ Built FAISS search index")
