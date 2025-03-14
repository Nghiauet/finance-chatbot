"""
Document Search Service for retrieving relevant financial documents based on user queries.
Provides methods for indexing, searching, and retrieving document content.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from pathlib import Path
import json
import os

from loguru import logger

class DocumentSearchService:
    """Service for searching and retrieving financial documents based on user queries."""
    
    def __init__(self, documents_path: Optional[str] = None):
        """
        Initialize the document search service.
        
        Args:
            documents_path: Path to the directory containing financial documents
        """
        self.documents_path = documents_path or os.environ.get("DOCUMENTS_PATH", "./data/documents")
        self.documents = []
        self._load_documents()
        logger.info(f"Initialized document search service with path: {self.documents_path}")
    
    def _load_documents(self) -> None:
        """Load documents from the specified directory."""
        try:
            documents_dir = Path(self.documents_path)
            if not documents_dir.exists():
                logger.warning(f"Documents directory not found: {self.documents_path}")
                return
            
            # Load all JSON files in the directory
            for file_path in documents_dir.glob("*.json"):
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        document = json.load(f)
                        self.documents.append(document)
                except Exception as e:
                    logger.error(f"Error loading document {file_path}: {str(e)}")
            
            logger.info(f"Loaded {len(self.documents)} documents")
        except Exception as e:
            logger.error(f"Error loading documents: {str(e)}")
    
    def search_documents(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Search for documents relevant to the given query.
        
        Args:
            query: The search query
            max_results: Maximum number of results to return
            
        Returns:
            List of relevant document dictionaries
        """
        if not self.documents:
            logger.warning("No documents available for search")
            return []
        
        # Simple keyword-based search implementation
        # In a production environment, this would be replaced with a more sophisticated
        # search algorithm or vector database for semantic search
        query_terms = query.lower().split()
        scored_documents = []
        
        for doc in self.documents:
            score = 0
            content = doc.get("content", "").lower()
            
            # Score based on term frequency
            for term in query_terms:
                if term in content:
                    score += content.count(term)
            
            # Boost score for matches in title or metadata
            for field in ["title", "company", "report_id", "type"]:
                field_value = str(doc.get(field, "")).lower()
                for term in query_terms:
                    if term in field_value:
                        score += 5  # Higher weight for metadata matches
            
            if score > 0:
                scored_documents.append((score, doc))
        
        # Sort by score (descending) and take top results
        scored_documents.sort(reverse=True, key=lambda x: x[0])
        results = [doc for _, doc in scored_documents[:max_results]]
        
        logger.info(f"Found {len(results)} documents matching query: '{query}'")
        return results
    
    def get_document_by_id(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific document by its ID.
        
        Args:
            document_id: The document ID to retrieve
            
        Returns:
            Document dictionary if found, None otherwise
        """
        for doc in self.documents:
            if doc.get("report_id") == document_id:
                return doc
        return None
    
    def refresh_documents(self) -> None:
        """Reload documents from the source directory."""
        self.documents = []
        self._load_documents()
        logger.info("Document index refreshed")
