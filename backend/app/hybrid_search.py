import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import threading
import time


try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    faiss = None


@dataclass
class HybridResult:
    person_id: str
    score: float
    source: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class IndexMetrics:
    total_vectors: int = 0
    search_time_ms: float = 0.0
    index_type: str = ""


class LRUEmbeddingCache:
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache: Dict[str, np.ndarray] = {}
        self.access_order: List[str] = []
        self.lock = threading.Lock()

    def get(self, person_id: str) -> Optional[np.ndarray]:
        with self.lock:
            if person_id in self.cache:
                self.access_order.remove(person_id)
                self.access_order.append(person_id)
                return self.cache[person_id].copy()
        return None

    def put(self, person_id: str, embedding: np.ndarray) -> None:
        with self.lock:
            if len(self.cache) >= self.max_size:
                lru = self.access_order.pop(0)
                del self.cache[lru]
            self.cache[person_id] = embedding.copy()
            self.access_order.append(person_id)

    def invalidate(self, person_id: str) -> None:
        with self.lock:
            self.cache.pop(person_id, None)
            if person_id in self.access_order:
                self.access_order.remove(person_id)


class HybridSearchEngine:
    def __init__(self, db_pool=None, num_shards: int = 4):
        self.dimension = 512
        self.db_pool = db_pool
        self.lru_cache = LRUEmbeddingCache()
        self.num_shards = num_shards
        self.hnsw_indexes = []
        self._init_indexes()

    def _init_indexes(self):
        if not FAISS_AVAILABLE:
            return
        for _ in range(self.num_shards):
            idx = faiss.IndexHNSWFlat(self.dimension, 32)
            idx.hnsw.efSearch = 128
            idx.hnsw.efConstruction = 200
            self.hnsw_indexes.append({"index": idx, "mapping": {}})

    def _get_shard(self, person_id: str) -> int:
        import hashlib
        hash_int = int(hashlib.md5(person_id.encode()).hexdigest(), 16)
        return hash_int % self.num_shards

    async def index_person(self, person_id: str, embedding: np.ndarray, metadata: Optional[Dict] = None) -> bool:
        cached = self.lru_cache.get(person_id)
        if cached is None:
            self.lru_cache.put(person_id, embedding)

        if FAISS_AVAILABLE and len(self.hnsw_indexes) > 0:
            shard_idx = self._get_shard(person_id)
            shard = self.hnsw_indexes[shard_idx]
            idx = len(shard["mapping"])
            shard["mapping"][idx] = person_id
            shard["index"].add(np.ascontiguousarray(embedding.reshape(1, -1).astype(np.float32)))

        if self.db_pool and metadata:
            async with self.db_pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO embeddings (person_id, embedding, camera_id)
                    VALUES ($1, $2, $3)
                """, person_id, embedding.tobytes(), metadata.get("camera_id"))

        return True

    def search(self, query_embedding: np.ndarray, k: int = 10, threshold: float = 0.4, use_ann: bool = True, use_db: bool = True) -> List[HybridResult]:
        start_time = time.time()
        results = {}

        if use_ann and FAISS_AVAILABLE:
            for shard in self.hnsw_indexes:
                try:
                    query = np.ascontiguousarray(query_embedding.reshape(1, -1).astype(np.float32))
                    distances, indices = shard["index"].search(query, k)
                    for dist, idx in zip(distances[0], indices[0]):
                        if idx >= 0 and idx in shard["mapping"]:
                            pid = shard["mapping"][idx]
                            score = 1.0 / (1.0 + dist)
                            results[pid] = HybridResult(person_id=pid, score=score, source="ann_index")
                except Exception:
                    pass

        sorted_results = sorted(results.values(), key=lambda x: x.score, reverse=True)[:k]
        return [r for r in sorted_results if r.score >= threshold]

    def get_metrics(self) -> IndexMetrics:
        total = sum(len(s["mapping"]) for s in self.hnsw_indexes)
        return IndexMetrics(total_vectors=total, index_type="hnsw" if FAISS_AVAILABLE else "pgvector_only")


class VectorStoreManager:
    def __init__(self, db_pool=None):
        self.db_pool = db_pool
        self.hybrid_engine = HybridSearchEngine(db_pool)
        self.initialized = False

    async def initialize(self, load_existing: bool = True):
        self.initialized = True

    async def search(self, query_embedding: np.ndarray, k: int = 10, threshold: float = 0.4) -> List[HybridResult]:
        return self.hybrid_engine.search(query_embedding, k, threshold)

    def get_metrics(self) -> Dict:
        index_metrics = self.hybrid_engine.get_metrics()
        return {"total_vectors": index_metrics.total_vectors, "index_type": index_metrics.index_type}


hybrid_store = None


async def init_vector_store(db_pool=None) -> VectorStoreManager:
    global hybrid_store
    hybrid_store = VectorStoreManager(db_pool)
    await hybrid_store.initialize()
    return hybrid_store


def get_vector_store() -> Optional[VectorStoreManager]:
    return hybrid_store