from __future__ import annotations

from pathlib import Path
import json
import pickle
import random
from typing import Any

import numpy as np

from dp_synth.config import PrivacyConfig
from dp_synth.types import ConversationDocument


class DialogueVectorStore:
    def __init__(self, persist_directory: str | Path, collection_name: str, preferred_backend: str = "auto") -> None:
        self.persist_directory = Path(persist_directory)
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.preferred_backend = preferred_backend
        self.backend_name = "local"
        self.client = None
        self.collection = None
        self._local_store_path = self.persist_directory / f"{self.collection_name}_local_store.pkl"
        self._local_records: list[dict[str, Any]] = []
        self._local_embeddings = np.empty((0, 0), dtype=np.float32)
        self._initialize_backend()

    def _initialize_backend(self) -> None:
        if self.preferred_backend in {"auto", "chroma"}:
            try:
                import chromadb

                self.client = chromadb.PersistentClient(path=str(self.persist_directory))
                self.collection = self.client.get_or_create_collection(name=self.collection_name)
                self.backend_name = "chroma"
                return
            except BaseException:
                self.client = None
                self.collection = None

        self.backend_name = "local"
        self._load_local_store()

    def reset(self) -> None:
        if self.backend_name == "chroma" and self.client is not None and self.collection is not None:
            try:
                self.client.delete_collection(self.collection.name)
            except BaseException:
                pass
            self.collection = self.client.get_or_create_collection(name=self.collection_name)
            return

        self._local_records = []
        self._local_embeddings = np.empty((0, 0), dtype=np.float32)
        if self._local_store_path.exists():
            self._local_store_path.unlink()

    def upsert_documents(
        self,
        documents: list[ConversationDocument],
        embeddings: list[list[float]],
    ) -> None:
        ids = [doc.conversation_id for doc in documents]
        texts = [doc.dialogue for doc in documents]
        metadatas = [self._normalize_metadata(doc.metadata) for doc in documents]

        if self.backend_name == "chroma" and self.collection is not None:
            try:
                self.collection.upsert(
                    ids=ids,
                    documents=texts,
                    metadatas=metadatas,
                    embeddings=embeddings,
                )
                return
            except BaseException:
                self.backend_name = "local"
                self.client = None
                self.collection = None

        self._local_records = [
            {"id": doc_id, "document": text, "metadata": metadata}
            for doc_id, text, metadata in zip(ids, texts, metadatas)
        ]
        self._local_embeddings = np.asarray(embeddings, dtype=np.float32)
        payload = {
            "records": self._local_records,
            "embeddings": self._local_embeddings,
        }
        with self._local_store_path.open("wb") as handle:
            pickle.dump(payload, handle)

    def retrieve(
        self,
        query_embedding: list[float],
        n_results: int,
        privacy: PrivacyConfig,
    ) -> list[dict]:
        if self.backend_name == "chroma" and self.collection is not None:
            try:
                result = self.collection.query(
                    query_embeddings=[query_embedding],
                    n_results=max(n_results * 3, n_results),
                    include=["documents", "metadatas", "distances"],
                )
                return self._rank_candidates(
                    documents=result.get("documents", [[]])[0],
                    metadatas=result.get("metadatas", [[]])[0],
                    distances=result.get("distances", [[]])[0],
                    n_results=n_results,
                    privacy=privacy,
                )
            except BaseException:
                self.backend_name = "local"
                self.client = None
                self.collection = None
                self._load_local_store()

        self._load_local_store()
        if self._local_embeddings.size == 0 or not self._local_records:
            return []

        query = np.asarray(query_embedding, dtype=np.float32)
        similarities = self._local_embeddings @ query
        candidate_count = min(len(similarities), max(n_results * 3, n_results))
        top_indices = np.argsort(-similarities)[:candidate_count]
        documents = [self._local_records[i]["document"] for i in top_indices]
        metadatas = [self._local_records[i]["metadata"] for i in top_indices]
        distances = [float(1.0 - similarities[i]) for i in top_indices]
        return self._rank_candidates(documents, metadatas, distances, n_results, privacy)

    def _load_local_store(self) -> None:
        if not self._local_store_path.exists():
            self._local_records = []
            self._local_embeddings = np.empty((0, 0), dtype=np.float32)
            return

        with self._local_store_path.open("rb") as handle:
            payload = pickle.load(handle)
        self._local_records = payload.get("records", [])
        self._local_embeddings = np.asarray(payload.get("embeddings", np.empty((0, 0))), dtype=np.float32)

    def _rank_candidates(
        self,
        documents: list[str],
        metadatas: list[dict],
        distances: list[float],
        n_results: int,
        privacy: PrivacyConfig,
    ) -> list[dict]:
        candidates: list[dict] = []
        for doc, metadata, distance in zip(documents, metadatas, distances):
            noisy_score = -float(distance)
            if privacy.enable_retrieval_noise:
                noisy_score += random.gammavariate(1.0, 1.0 / max(privacy.epsilon, 1e-6))
                noisy_score -= random.gammavariate(1.0, 1.0 / max(privacy.epsilon, 1e-6))
            candidates.append(
                {
                    "document": doc,
                    "metadata": metadata or {},
                    "distance": float(distance),
                    "score": noisy_score,
                }
            )

        candidates.sort(key=lambda item: item["score"], reverse=True)
        return candidates[:n_results]

    @staticmethod
    def _normalize_metadata(metadata: dict) -> dict:
        normalized = {}
        for key, value in metadata.items():
            if value is None:
                normalized[key] = ""
            elif isinstance(value, (str, int, float, bool)):
                normalized[key] = value
            else:
                normalized[key] = str(value)
        return normalized
