"""
Episodic Memory layer for LangGraph DevOps multi-agent system.
Stores and retrieves past incident resolutions using Pinecone vector storage.
"""

import os
import logging
from typing import Dict, Any, List

from langchain_pinecone import PineconeVectorStore
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Configure logger
logger = logging.getLogger(__name__)


class CloudEpisodicMemory:
    """
    Cloud vector vault for storing successful incident resolutions and
    searching for past similar crashes using cosine similarity.
    """

    def __init__(self) -> None:
        """
        Initialize the Pinecone vector store and embedding model.

        Raises:
            ValueError: If PINECONE_API_KEY, PINECONE_INDEX_NAME, or GEMINI_API_KEY is missing.
        """
        pinecone_api_key = os.getenv("PINECONE_API_KEY")
        pinecone_index_name = os.getenv("PINECONE_INDEX_NAME")
        gemini_api_key = os.getenv("GEMINI_API_KEY")

        if not pinecone_api_key:
            raise ValueError("PINECONE_API_KEY environment variable is required.")
        if not pinecone_index_name:
            raise ValueError("PINECONE_INDEX_NAME environment variable is required.")
        if not gemini_api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required.")

        # Set Pinecone environment variable (required by the underlying client)
        os.environ["PINECONE_API_KEY"] = pinecone_api_key

        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/embedding-001",
            google_api_key=gemini_api_key,
        )
        self.vector_store = PineconeVectorStore(
            index_name=pinecone_index_name,
            embedding=self.embeddings,
        )
        logger.info(f"CloudEpisodicMemory initialized with index: {pinecone_index_name}")

    def store_resolution(self, incident_id: str, error_logs: str, rca_report: str) -> bool:
        """
        Store a resolved incident with its error logs and RCA report into Pinecone.

        Args:
            incident_id: Unique identifier for the incident.
            error_logs: Raw error logs or stack trace.
            rca_report: Final root cause analysis report (Markdown/text).

        Returns:
            True if storage succeeded, False otherwise.
        """
        # Combine the error logs and RCA report into a rich text document
        document = f"Incident ID: {incident_id}\n\nError Logs:\n{error_logs}\n\nRCA Report:\n{rca_report}"
        metadata = {
            "incident_id": incident_id,
            "type": "resolved_crash",
        }

        try:
            self.vector_store.add_texts(
                texts=[document],
                metadatas=[metadata],
            )
            logger.info(f"Successfully stored incident {incident_id} in Pinecone.")
            return True
        except Exception as e:
            logger.error(f"Failed to store incident {incident_id}: {e}")
            return False

    def search_past_incidents(self, current_error_log: str, top_k: int = 2) -> List[Dict[str, Any]]:
        """
        Search for past incidents similar to the current error log.

        Args:
            current_error_log: The error log from the current incident.
            top_k: Number of similar incidents to retrieve (default: 2).

        Returns:
            A list of dictionaries, each containing:
                - "incident_id": the stored incident identifier
                - "content": the historical RCA report (and logs) that matched
            Returns an empty list on error or if no matches.
        """
        try:
            results = self.vector_store.similarity_search(
                current_error_log,
                k=top_k,
            )
            output = []
            for doc in results:
                # Extract incident_id from metadata; fallback to "unknown"
                incident_id = doc.metadata.get("incident_id", "unknown")
                output.append({
                    "incident_id": incident_id,
                    "content": doc.page_content,
                })
            logger.info(f"Found {len(output)} past incidents similar to current error.")
            return output
        except Exception as e:
            logger.error(f"Error searching past incidents: {e}")
            return []