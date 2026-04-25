import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import threading
import queue
import asyncio


try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    faiss = None


@dataclass
class IndexStats:
    total_vectors: int = 0
    index_size_mb: float = 0.0
    search_latency_p50_ms: float = 0.0
    search_latency_p99_ms: float = 0.0
    build_time_ms: float = 0.0
    recall_at_10: float = 0.0


class VectorShard:
    """A single vector index shard."""
    
    def __init__(
        self,
        shard_id: str,
        dimension: int = 512,
        index_type: str = "hnsw"
    ):
        self.shard_id = shard_id
        self.dimension = dimension
        self.index_type = index_type
        self.index = None
        self.mapping = []  # person_id -> index position
        self.lock = threading.RLock()
        
        self._build_index()
    
    def _build_index(self) -> None:
        """Build the FAISS index."""
        if not FAISS_AVAILABLE:
            return
            
        if self.index_type == "hnsw":
            # HNSW - good for dynamic workloads
            self.index = faiss.IndexHNSWFlat(self.dimension, 32)
            self.index.hnsw.efSearch = 128
            self.index.hnsw.efConstruction = 200
        elif self.index_type == "ivf":
            # IVF - good for large datasets
            quantizer = faiss.IndexFlatL2(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)
            self.index.nprobe = 32
        else:
            # Brute force fallback
            self.index = faiss.IndexFlatL2(self.dimension)
    
    def add_vectors(
        self,
        vectors: np.ndarray,
        person_ids: List[str]
    ) -> None:
        """Add vectors to index."""
        if not FAISS_AVAILABLE or self.index is None:
            return
            
        vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        
        with self.lock:
            start_idx = len(self.mapping)
            self.mapping.extend(person_ids)
            
            if self.index_type == "ivf" and not self.index.is_trained:
                # Train on sufficient samples
                if len(vectors) >= 100:
                    self.index.train(vectors[:100])
                else:
                    # Fallback to direct add
                    self.index = faiss.IndexFlatL2(self.dimension)
            
            self.index.add(vectors)
    
    def search(
        self,
        query: np.ndarray,
        k: int = 10
    ) -> Tuple[np.ndarray, np.ndarray]:
        """Search the index."""
        if not FAISS_AVAILABLE or self.index is None:
            return np.array([]), np.array([])
        
        query = np.ascontiguousarray(query.reshape(1, -1), dtype=np.float32)
        
        with self.lock:
            distances, indices = self.index.search(query, k)
        
        # Convert distances to scores
        scores = 1.0 / (1.0 + distances)
        
        # Map to person_ids
        person_ids = []
        for idx in indices[0]:
            if idx >= 0 and idx < len(self.mapping):
                person_ids.append(self.mapping[idx])
            else:
                person_ids.append(None)
        
        return scores[0], np.array(person_ids)
    
    def remove_vectors(self, person_ids: List[str]) -> int:
        """Remove vectors by person_id."""
        # FAISS doesn't support efficient removal
        # Mark as deleted and rebuild periodically
        removed = 0
        with self.lock:
            for pid in person_ids:
                if pid in self.mapping:
                    self.mapping[self.mapping.index(pid)] = None
                    removed += 1
        return removed
    
    def get_stats(self) -> Dict:
        """Get shard statistics."""
        return {
            "shard_id": self.shard_id,
            "total_vectors": len(self.mapping) if self.index else 0,
            "index_type": self.index_type
        }


class VectorShardManager:
    """Manages sharded vector indices for scalability."""
    
    def __init__(
        self,
        num_shards: int = 4,
        dimension: int = 512,
        index_type: str = "hnsw"
    ):
        self.num_shards = num_shards
        self.dimension = dimension
        self.index_type = index_type
        self.shards: Dict[str, VectorShard] = {}
        self.shard_lock = threading.RLock()
        
        # Initialize shards
        for i in range(num_shards):
            shard_id = f"shard_{i}"
            self.shards[shard_id] = VectorShard(shard_id, dimension, index_type)
    
    def _get_shard_for_id(self, person_id: str) -> str:
        """Determine shard for a person_id using stable consistent hashing."""
        import hashlib
        # Use MD5 hash for stable distribution across processes
        hash_int = int(hashlib.md5(person_id.encode()).hexdigest(), 16)
        shard_idx = hash_int % self.num_shards
        return f"shard_{shard_idx}"
    
    def add_vectors(
        self,
        vectors: np.ndarray,
        person_ids: List[str]
    ) -> None:
        """Add vectors to appropriate shards."""
        # Group by shard
        by_shard = {}
        
        for vec, pid in zip(vectors, person_ids):
            shard_id = self._get_shard_for_id(pid)
            if shard_id not in by_shard:
                by_shard[shard_id] = {"vectors": [], "ids": []}
            by_shard[shard_id]["vectors"].append(vec)
            by_shard[shard_id]["ids"].append(pid)
        
        # Add to each shard
        for shard_id, data in by_shard.items():
            if shard_id in self.shards:
                self.shards[shard_id].add_vectors(
                    np.array(data["vectors"]),
                    data["ids"]
                )
    
    def search(
        self,
        query: np.ndarray,
        k: int = 10,
        threshold: float = 0.4
    ) -> List[Dict]:
        """Search across all shards and merge results."""
        all_results = []
        
        # Search shards in parallel
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_shards) as executor:
            futures = {
                executor.submit(
                    self.shards[sid].search, query, k
                ): sid
                for sid in self.shards
            }
            
            for future in concurrent.futures.as_completed(futures):
                shard_id = futures[future]
                try:
                    scores, person_ids = future.result()
                    
                    for score, pid in zip(scores, person_ids):
                        if pid is not None and score > threshold:
                            all_results.append({
                                "person_id": pid,
                                "score": float(score),
                                "shard": shard_id
                            })
                except Exception:
                    pass
        
        # Merge and deduplicate (keep highest score)
        merged = {}
        for r in all_results:
            pid = r["person_id"]
            if pid not in merged or r["score"] > merged[pid]["score"]:
                merged[pid] = r
        
        # Sort and return top k
        results = sorted(merged.values(), key=lambda x: x["score"], reverse=True)
        return results[:k]
    
    def remove_vectors(self, person_ids: List[str]) -> int:
        """Remove vectors from shards."""
        total_removed = 0
        
        for pid in person_ids:
            shard_id = self._get_shard_for_id(pid)
            if shard_id in self.shards:
                removed = self.shards[shard_id].remove_vectors([pid])
                total_removed += removed
        
        return total_removed
    
    def rebuild_shard(self, shard_id: str) -> None:
        """Rebuild a shard (for garbage collection)."""
        if shard_id not in self.shards:
            return
        
        # Get all valid vectors
        shard = self.shards[shard_id]
        
        with shard.lock:
            valid_ids = [pid for pid in shard.mapping if pid is not None]
        
        # For full rebuild, would need to fetch from DB
        # This is a placeholder
    
    def get_stats(self) -> IndexStats:
        """Get aggregate statistics."""
        total_vectors = sum(
            len(s.mapping) for s in self.shards.values()
        )
        
        return IndexStats(total_vectors=total_vectors)


class GPUBatcher:
    """GPU inference batching for optimal throughput."""
    
    def __init__(self, batch_size: int = 32):
        self.batch_size = batch_size
        self.queue = queue.Queue()
        self.results = {}
        self.callbacks = {}
        
    def add_request(
        self,
        request_id: str,
        images: List[np.ndarray],
        callback=None
    ) -> None:
        """Add request to batch queue."""
        self.queue.put({
            "request_id": request_id,
            "images": images,
            "callback": callback,
            "timestamp": np.datetime64('now')
        })
    
    def process_batch(self) -> None:
        """Process queued requests in batches."""
        if self.queue.empty():
            return
        
        # Gather up to batch_size requests
        batch = []
        request_ids = []
        
        while len(batch) < self.batch_size and not self.queue.empty():
            try:
                item = self.queue.get_nowait()
                batch.extend(item["images"])
                request_ids.append(item["request_id"])
            except queue.Empty:
                break
        
        if not batch:
            return
        
        # Would process on GPU here
        # embeddings = gpu_model(batch)
        
        # Distribute results
        # (Simplified placeholder)


class CachedIndex:
    """LRU cache for frequently accessed embeddings."""
    
    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self.cache = {}
        self.access_count = {}
        self.lock = threading.RLock()
    
    def get(self, person_id: str) -> Optional[np.ndarray]:
        """Get cached embedding."""
        with self.lock:
            if person_id in self.cache:
                self.access_count[person_id] = self.access_count.get(person_id, 0) + 1
                return self.cache[person_id]
        return None
    
    def put(self, person_id: str, embedding: np.ndarray) -> None:
        """Cache embedding."""
        with self.lock:
            if len(self.cache) >= self.max_size:
                # Evict least accessed
                lru = min(
                    self.cache.keys(),
                    key=lambda k: self.access_count.get(k, 0)
                )
                del self.cache[lru]
                del self.access_count[lru]
            
            self.cache[person_id] = embedding
            self.access_count[person_id] = 1
    
    def invalidate(self, person_id: str) -> None:
        """Invalidate cached embedding."""
        with self.lock:
            self.cache.pop(person_id, None)
            self.access_count.pop(person_id, None)


# Global instances
shard_manager = None
cached_index = CachedIndex()
gpu_batcher = GPUBatcher()


def init_shard_manager(num_shards: int = 4) -> VectorShardManager:
    """Initialize sharded index manager."""
    global shard_manager
    shard_manager = VectorShardManager(num_shards=num_shards)
    return shard_manager


def get_shard_manager() -> Optional[VectorShardManager]:
    """Get the global shard manager."""
    return shard_manager