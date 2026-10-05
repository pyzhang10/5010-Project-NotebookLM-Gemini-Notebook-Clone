from __future__ import annotations

import math
import re
import time
from dataclasses import dataclass

import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from rank_bm25 import BM25Okapi

from config import EMBEDDING_MODEL, TOP_K
from models import Chunk
from storage import LocalStorage


@dataclass
class SearchResult:
    chunk_id: str
    text: str
    metadata: dict
    score: float


class VectorIndex:
    def __init__(self, storage: LocalStorage):
        self.storage = storage
        self.embedding = SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )

    def _collection(self, notebook_id: str):
        directory = self.storage.path(notebook_id) / "vector_db"
        client = chromadb.PersistentClient(path=str(directory))
        return client.get_or_create_collection(
            "notebook_chunks",
            embedding_function=self.embedding,
            metadata={"hnsw:space": "cosine"},
        )

    def add(self, notebook_id: str, chunks: list[Chunk]) -> None:
        collection = self._collection(notebook_id)
        collection.upsert(
            ids=[item.id for item in chunks],
            documents=[item.text for item in chunks],
            metadatas=[item.metadata() for item in chunks],
        )

    def all(self, notebook_id: str) -> list[SearchResult]:
        data = self._collection(notebook_id).get(include=["documents", "metadatas"])
        return [
            SearchResult(chunk_id=chunk_id, text=text, metadata=metadata, score=0.0)
            for chunk_id, text, metadata in zip(
                data.get("ids", []), data.get("documents", []), data.get("metadatas", [])
            )
        ]

    def vector_search(self, notebook_id: str, query: str, top_k: int = TOP_K) -> list[SearchResult]:
        collection = self._collection(notebook_id)
        if collection.count() == 0:
            return []
        result = collection.query(
            query_texts=[query],
            n_results=min(top_k, collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        return [
            SearchResult(
                chunk_id=chunk_id,
                text=text,
                metadata=metadata,
                score=1.0 - float(distance),
            )
            for chunk_id, text, metadata, distance in zip(
                result["ids"][0], result["documents"][0],
                result["metadatas"][0], result["distances"][0],
            )
        ]

    @staticmethod
    def _tokens(value: str) -> list[str]:
        return re.findall(r"[a-z0-9_]+", value.lower())

    def hybrid_search(self, notebook_id: str, query: str, top_k: int = TOP_K) -> list[SearchResult]:
        documents = self.all(notebook_id)
        if not documents:
            return []
        candidate_k = min(max(top_k * 3, 10), len(documents))
        dense = self.vector_search(notebook_id, query, candidate_k)
        bm25 = BM25Okapi([self._tokens(item.text) for item in documents])
        keyword_scores = bm25.get_scores(self._tokens(query))
        keyword_order = sorted(
            range(len(documents)), key=lambda index: keyword_scores[index], reverse=True
        )[:candidate_k]

        # Reciprocal Rank Fusion is robust even though BM25 and cosine scores
        # have different numerical scales.
        fused: dict[str, float] = {}
        by_id = {item.chunk_id: item for item in documents}
        for rank, item in enumerate(dense, start=1):
            fused[item.chunk_id] = fused.get(item.chunk_id, 0.0) + 1 / (60 + rank)
        for rank, index in enumerate(keyword_order, start=1):
            item = documents[index]
            fused[item.chunk_id] = fused.get(item.chunk_id, 0.0) + 1 / (60 + rank)
        ordered = sorted(fused, key=fused.get, reverse=True)[:top_k]
        return [
            SearchResult(
                chunk_id=chunk_id, text=by_id[chunk_id].text,
                metadata=by_id[chunk_id].metadata, score=fused[chunk_id],
            )
            for chunk_id in ordered
        ]

    def search(self, notebook_id: str, query: str, method: str, top_k: int = TOP_K):
        started = time.perf_counter()
        if method == "Vector Search":
            results = self.vector_search(notebook_id, query, top_k)
        else:
            results = self.hybrid_search(notebook_id, query, top_k)
        return results, time.perf_counter() - started

