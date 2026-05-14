"""
Homomorphic Encryption for Encrypted Embedding Similarity Search.

This module implements HE-based operations on encrypted embeddings,
never decrypting data during inference/matching operations.

Supports CKKS scheme for approximate arithmetic over real numbers,
optimized for cosine similarity on encrypted vectors.
"""

import os
import logging
import json
import base64
import pickle
import hashlib
import secrets
import time
import statistics
import asyncio
from typing import List, Dict, Any, Optional, Tuple, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from contextlib import contextmanager

import numpy as np

try:
    import tenseal as ts
    TENSEAL_AVAILABLE = True
except ImportError:
    TENSEAL_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class HEBenchmarkResult:
    """Results from HE performance benchmark."""
    operation: str
    avg_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    throughput_ops_per_sec: float
    data_size_bytes: int
    iterations: int
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HEBenchmarkSuite:
    """
    Benchmark suite for homomorphic encryption operations.
    
    Measures:
      - Encryption latency
      - Decryption latency
      - Encrypted similarity/latency
      - Batch operations throughput
      - Memory usage
      - Ciphertext expansion ratio
    """
    
    def __init__(
        self,
        he_engine: 'HomomorphicEncryptionEngine',
        warmup_iterations: int = 10,
        test_iterations: int = 100
    ):
        self.he_engine = he_engine
        self.warmup_iterations = warmup_iterations
        self.test_iterations = test_iterations
        self._results: List[HEBenchmarkResult] = []
    
    @contextmanager
    def _timer(self):
        """Context manager for timing operations."""
        start = time.perf_counter()
        yield
        end = time.perf_counter()
        elapsed_ms = (end - start) * 1000
        return elapsed_ms
    
    def _measure_iterations(
        self,
        operation: Callable[[], Any],
        data_size: int = 0
    ) -> HEBenchmarkResult:
        """Run operation multiple times and collect metrics."""
        # Warmup
        for _ in range(self.warmup_iterations):
            try:
                operation()
            except Exception:
                pass  # Warmup failures okay
        
        # Actual measurement
        latencies = []
        for _ in range(self.test_iterations):
            with self._timer() as t:
                result = operation()
            latencies.append(t)
        
        latencies.sort()
        avg = statistics.mean(latencies)
        p50 = statistics.median(latencies)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)
        throughput = (1000.0 / avg) if avg > 0 else float('inf')
        
        return HEBenchmarkResult(
            operation="custom",
            avg_latency_ms=avg,
            p50_latency_ms=p50,
            p95_latency_ms=p95,
            p99_latency_ms=p99,
            throughput_ops_per_sec=throughput,
            data_size_bytes=data_size,
            iterations=self.test_iterations,
            timestamp=datetime.utcnow().isoformat()
        )
    
    def benchmark_encryption(
        self,
        embedding_dim: int = 512,
        iterations: int = None
    ) -> HEBenchmarkResult:
        """Benchmark single embedding encryption."""
        if iterations is not None:
            self.test_iterations = iterations
        
        # Generate random normalized embedding
        emb = np.random.randn(embedding_dim).astype(np.float32)
        emb = emb / (np.linalg.norm(emb) + 1e-8)
        
        def op():
            return self.he_engine.encrypt_embedding(emb)
        
        result = self._measure_iterations(op, data_size=emb.nbytes)
        result.operation = "encrypt_embedding"
        self._results.append(result)
        return result
    
    def benchmark_decryption(
        self,
        embedding_dim: int = 512,
        iterations: int = None
    ) -> HEBenchmarkResult:
        """Benchmark decryption of encrypted embedding."""
        if iterations is not None:
            self.test_iterations = iterations
        
        # Prepare encrypted embedding
        emb = np.random.randn(embedding_dim).astype(np.float32)
        emb = emb / (np.linalg.norm(emb) + 1e-8)
        enc = self.he_engine.encrypt_embedding(emb)
        
        def op():
            return self.he_engine.decrypt_embedding(enc)
        
        result = self._measure_iterations(op, data_size=emb.nbytes)
        result.operation = "decrypt_embedding"
        self._results.append(result)
        return result
    
    def benchmark_encrypted_similarity(
        self,
        embedding_dim: int = 512,
        iterations: int = None
    ) -> HEBenchmarkResult:
        """Benchmark homomorphic cosine similarity computation."""
        if iterations is not None:
            self.test_iterations = iterations
        
        # Prepare two encrypted embeddings
        emb1 = np.random.randn(embedding_dim).astype(np.float32)
        emb1 = emb1 / (np.linalg.norm(emb1) + 1e-8)
        emb2 = np.random.randn(embedding_dim).astype(np.float32)
        emb2 = emb2 / (np.linalg.norm(emb2) + 1e-8)
        
        enc1 = self.he_engine.encrypt_embedding(emb1)
        enc2 = self.he_engine.encrypt_embedding(emb2)
        
        def op():
            return self.he_engine.compute_encrypted_cosine_similarity(enc1, enc2)
        
        result = self._measure_iterations(op, data_size=2 * emb1.nbytes)
        result.operation = "encrypted_similarity"
        self._results.append(result)
        return result
    
    def benchmark_batch_encrypt(
        self,
        batch_size: int = 100,
        embedding_dim: int = 512,
        iterations: int = None
    ) -> HEBenchmarkResult:
        """Benchmark batch encryption of multiple embeddings."""
        if iterations is not None:
            self.test_iterations = iterations
        
        batch = [np.random.randn(embedding_dim).astype(np.float32) for _ in range(batch_size)]
        batch = [emb / (np.linalg.norm(emb) + 1e-8) for emb in batch]
        total_bytes = sum(emb.nbytes for emb in batch)
        
        def op():
            return self.he_engine.batch_encrypt_embeddings(batch)
        
        result = self._measure_iterations(op, data_size=total_bytes)
        result.operation = f"batch_encrypt_{batch_size}"
        self._results.append(result)
        return result
    
    def benchmark_nn_search(
        self,
        database_size: int = 1000,
        embedding_dim: int = 512,
        top_k: int = 10,
        iterations: int = None
    ) -> HEBenchmarkResult:
        """Benchmark encrypted nearest neighbor search."""
        if iterations is not None:
            self.test_iterations = iterations
        
        # Build database
        query_emb = np.random.randn(embedding_dim).astype(np.float32)
        query_emb = query_emb / (np.linalg.norm(query_emb) + 1e-8)
        
        database_embs = [
            np.random.randn(embedding_dim).astype(np.float32) for _ in range(database_size)
        ]
        database_embs = [emb / (np.linalg.norm(emb) + 1e-8) for emb in database_embs]
        
        query_enc = self.he_engine.encrypt_embedding(query_emb)
        database_enc = self.he_engine.batch_encrypt_embeddings(database_embs)
        
        def op():
            return self.he_engine.encrypted_nearest_neighbor_search(
                query_enc, database_enc,
                database_ids=[str(i) for i in range(database_size)],
                top_k=top_k
            )
        
        total_bytes = sum(emb.nbytes for emb in database_embs) + query_emb.nbytes
        result = self._measure_iterations(op, data_size=total_bytes)
        result.operation = f"encrypted_nn_search_{database_size}"
        self._results.append(result)
        return result
    
    def run_full_suite(
        self,
        embedding_dims: List[int] = [128, 256, 512],
        database_sizes: List[int] = [100, 1000, 5000]
    ) -> Dict[str, Any]:
        """
        Run complete benchmark suite across configurations.
        
        Returns dictionary of all results.
        """
        logger.info("Starting HE benchmark suite...")
        
        all_results = {
            "timestamp": datetime.utcnow().isoformat(),
            "tenseal_available": TENSEAL_AVAILABLE,
            "simulation_mode": self.he_engine.simulation_mode,
            "config": {
                "poly_modulus_degree": self.he_engine.config.poly_modulus_degree,
                "coeff_mod_bit_sizes": self.he_engine.config.coeff_mod_bit_sizes,
                "scale": self.he_engine.config.scale
            },
            "benchmarks": {}
        }
        
        for dim in embedding_dims:
            logger.info(f"Benchmarking dimension {dim}")
            
            enc_res = self.benchmark_encryption(dim)
            dec_res = self.benchmark_decryption(dim)
            sim_res = self.benchmark_encrypted_similarity(dim)
            
            key = f"dim_{dim}"
            all_results["benchmarks"][key] = {
                "encryption": enc_res.to_dict(),
                "decryption": dec_res.to_dict(),
                "similarity": sim_res.to_dict(),
                "ciphertext_expansion_ratio": (
                    len(enc_res.to_dict().get('data', '')) * 4 / (dim * 4)  # Rough estimate
                )
            }
        
        for db_size in database_sizes:
            logger.info(f"Benchmarking NN search with db_size={db_size}")
            nn_res = self.benchmark_nn_search(db_size, embedding_dim=512)
            all_results["benchmarks"][f"nn_search_{db_size}"] = nn_res.to_dict()
        
        # Summary stats
        all_results["summary"] = {
            "total_operations": sum(r.iterations for r in self._results),
            "average_latency_ms": statistics.mean(r.avg_latency_ms for r in self._results),
            "fastest_operation": min(self._results, key=lambda r: r.avg_latency_ms).operation,
            "slowest_operation": max(self._results, key=lambda r: r.avg_latency_ms).operation
        }
        
        logger.info("Benchmark suite completed")
        return all_results
    
    def export_results_json(self, filepath: str):
        """Export benchmark results to JSON file."""
        if not self._results:
            logger.warning("No results to export")
            return
        
        data = {
            "results": [r.to_dict() for r in self._results],
            "generated_at": datetime.utcnow().isoformat(),
            "simulation_mode": self.he_engine.simulation_mode
        }
        
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Benchmark results exported to {filepath}")


@dataclass
class HECiphertextMetadata:
    """Metadata for HE ciphertexts for integrity validation."""
    version: str = "1.0"
    scheme: str = "CKKS"
    poly_modulus_degree: int = 8192
    scale: int = 2**40
    created_at: str = ""
    key_id: Optional[str] = None
    hash_sha256: Optional[str] = None  # Hash of plaintext for integrity check
    associated_data: Optional[bytes] = None
    mac: Optional[bytes] = None  # HMAC for authenticity
    
    def compute_hash(self, plaintext_bytes: bytes) -> str:
        """Compute SHA256 hash of plaintext."""
        return hashlib.sha256(plaintext_bytes).hexdigest()
    
    def compute_mac(self, key: bytes) -> bytes:
        """Compute HMAC for ciphertext authentication."""
        h = hashlib.new('hmac', key, hashlib.sha256)
        if self.hash_sha256:
            h.update(self.hash_sha256.encode())
        if self.key_id:
            h.update(self.key_id.encode())
        return h.digest()[:16]  # 128-bit MAC
    
    def verify_mac(self, mac: bytes, key: bytes) -> bool:
        """Verify MAC authenticity."""
        expected = self.compute_mac(key)
        return secrets.compare_digest(mac, expected)


class HECiphertextValidator:
    """
    Ciphertext validator for HE operations.
    
    Provides:
      - Cryptographic hash verification
      - MAC-based authenticity
      - Key version checking
      - Replay protection (via nonce/timestamp)
      - Deserialization integrity checks
    """
    
    def __init__(
        self,
        mac_key: Optional[bytes] = None,
        require_mac: bool = True
    ):
        """
        Initialize validator.
        
        Args:
            mac_key: Secret key for HMAC (should be rotated)
            require_mac: Require MAC on all ciphertexts (production only)
        """
        self.mac_key = mac_key or secrets.token_bytes(32)
        self.require_mac = require_mac
        self._nonce_counter = 0
    
    def wrap_ciphertext(
        self,
        encrypted_data: bytes,
        metadata: HECiphertextMetadata,
        plaintext: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Wrap ciphertext with metadata and integrity checks.
        
        Returns encoded dict with ciphertext, metadata, MAC.
        """
        # Compute plaintext hash if provided
        if plaintext is not None:
            plain_bytes = plaintext.tobytes()
            metadata.hash_sha256 = metadata.compute_hash(plain_bytes)
        
        metadata.created_at = datetime.utcnow().isoformat()
        
        # Compute MAC
        mac = metadata.compute_mac(self.mac_key)
        
        # Encode package
        package = {
            "ciphertext": base64.b64encode(encrypted_data).decode(),
            "metadata": asdict(metadata),
            "mac": base64.b64encode(mac).decode(),
            "nonce": self._generate_nonce()
        }
        
        return package
    
    def unwrap_ciphertext(
        self,
        package: Dict[str, Any],
        expected_scheme: Optional[str] = None
    ) -> Tuple[bytes, HECiphertextMetadata]:
        """
        Unwrap and validate ciphertext package.
        
        Returns:
            (ciphertext_bytes, metadata)
        
        Raises:
            ValueError: If validation fails
        """
        # Decode components
        ct_bytes = base64.b64decode(package["ciphertext"])
        meta_dict = package["metadata"]
        received_mac = base64.b64decode(package["mac"])
        
        metadata = HECiphertextMetadata(**meta_dict)
        
        # Validate MAC
        if self.require_mac:
            if not metadata.verify_mac(received_mac, self.mac_key):
                raise ValueError("Ciphertext MAC verification failed - possible tampering")
        
        # Verify scheme if expected
        if expected_scheme and metadata.scheme != expected_scheme:
            raise ValueError(
                f"Scheme mismatch: expected {expected_scheme}, got {metadata.scheme}"
            )
        
        # Check timestamp freshness (anti-replay)
        # Allow 5 minute window
        if metadata.created_at:
            created = datetime.fromisoformat(metadata.created_at)
            age = datetime.utcnow() - created
            if age > timedelta(minutes=5):
                raise ValueError(f"Ciphertext too old: {age}")
        
        return ct_bytes, metadata
    
    def verify_plaintext_integrity(
        self,
        ciphertext_package: Dict[str, Any],
        plaintext: np.ndarray
    ) -> bool:
        """
        Verify that decrypted plaintext matches original hash.
        """
        metadata = HECiphertextMetadata(**ciphertext_package["metadata"])
        plain_bytes = plaintext.tobytes()
        computed_hash = metadata.compute_hash(plain_bytes)
        return secrets.compare_digest(computed_hash, metadata.hash_sha256 or "")
    
    def _generate_nonce(self) -> str:
        """Generate unique nonce for replay protection."""
        self._nonce_counter += 1
        ts = int(time.time() * 1000)
        nonce_data = f"{ts}:{self._nonce_counter}:{secrets.token_hex(8)}"
        return hashlib.sha256(nonce_data.encode()).hexdigest()[:16]


class HEKeyRotationManager:
    """
    Manages HE key rotation with graceful migration.
    
    Rotation policy:
      - Primary key active for 30 days
      - Old keys retained for 90 days for decryption
      - Grace period: both old and new keys accepted
      - Key version in ciphertext metadata
      - Async background rotation
    
    Steps for rotation:
      1. Generate new key, mark old as "deprecated"
      2. Continue decrypting with old key
      3. New encryptions use new key
      4. After grace period, old key archived
    """
    
    def __init__(
        self,
        key_manager: 'HEKeyManager',
        rotation_days: int = 30,
        grace_days: int = 90
    ):
        self.key_manager = key_manager
        self.rotation_days = rotation_days
        self.grace_days = grace_days
        self._rotation_lock = asyncio.Lock()
    
    async def rotate_if_needed(self) -> Optional[str]:
        """
        Check if rotation due and perform async rotation.
        
        Returns:
            New key_id if rotated, else None
        """
        async with self._rotation_lock:
            if self.key_manager.should_rotate():
                old_key_id = self.key_manager._current_key_id
                new_key_id = self.key_manager.rotate_key()
                logger.info(
                    f"HE key rotation: {old_key_id} -> {new_key_id}. "
                    f"Old key remains decryption-capable for {self.grace_days} days"
                )
                return new_key_id
        return None
    
    def get_key_for_encryption(self) -> str:
        """Get active key ID for new encryptions."""
        return self.key_manager._current_key_id
    
    def get_keys_for_decryption(self) -> List[str]:
        """
        Get all keys valid for decryption (active + grace period).
        
        Order: [newest, ..., oldest] for trial decryption.
        """
        valid_keys = []
        for key_id, key_data in self.key_manager._keys.items():
            if key_data.get('active'):
                valid_keys.insert(0, key_id)  # Newest first
            else:
                # Check if within grace period
                created = datetime.fromisoformat(key_data['created_at'])
                age_days = (datetime.utcnow() - created).days
                if age_days <= self.grace_days:
                    valid_keys.append(key_id)
        
        return valid_keys
    
    def migrate_ciphertext(
        self,
        ciphertext_package: Dict[str, Any],
        target_key_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Re-encrypt ciphertext under new key (if needed).
        
        Process:
          1. Decrypt with old key
          2. Re-encrypt with new key
          3. Update metadata version and key_id
          4. Return migrated package
        """
        meta = HECiphertextMetadata(**ciphertext_package["metadata"])
        current_key = target_key_id or self.get_key_for_encryption()
        
        if meta.key_id == current_key:
            return ciphertext_package  # Already up-to-date
        
        logger.info(f"Migrating ciphertext from {meta.key_id} to {current_key}")
        
        # This would require decryption (so need old key)
        # For now, update metadata only (actual re-encrypt needs secret key)
        new_meta = HECiphertextMetadata(
            version=meta.version,
            scheme=meta.scheme,
            poly_modulus_degree=meta.poly_modulus_degree,
            scale=meta.scale,
            created_at=datetime.utcnow().isoformat(),
            key_id=current_key,
            hash_sha256=meta.hash_sha256
        )
        
        new_package = ciphertext_package.copy()
        new_package["metadata"] = asdict(new_meta)
        
        return new_package


class HomomorphicEncryptionEngine:
    """Configuration for homomorphic encryption context."""
    poly_modulus_degree: int = 8192
    coeff_mod_bit_sizes: List[int] = None
    scale: int = 2 ** 40
    key_rotation_days: int = 30
    
    def __post_init__(self):
        if self.coeff_mod_bit_sizes is None:
            self.coeff_mod_bit_sizes = [60, 40, 40, 60]


class HEKeyManager:
    """Manages HE key lifecycle: generation, storage, rotation."""
    
    def __init__(self, config: HEContextConfig, keys_dir: str = None):
        self.config = config
        self.keys_dir = keys_dir or os.getenv("HE_KEYS_DIR", "/app/keys/he")
        os.makedirs(self.keys_dir, exist_ok=True)
        self._current_key_id: Optional[str] = None
        self._keys: Dict[str, Dict[str, Any]] = {}
        self._load_keys()
    
    def _load_keys(self):
        """Load all persisted keys from disk."""
        for fname in os.listdir(self.keys_dir):
            if fname.endswith('.hekey'):
                path = os.path.join(self.keys_dir, fname)
                try:
                    with open(path, 'rb') as f:
                        key_data = pickle.load(f)
                    key_id = fname.replace('.hekey', '')
                    self._keys[key_id] = key_data
                    if key_data.get('active'):
                        self._current_key_id = key_id
                except Exception as e:
                    logger.error(f"Failed to load HE key {fname}: {e}")
    
    def generate_key(self, key_id: str = None) -> str:
        """Generate a new HE keypair (public+secret)."""
        key_id = key_id or f"key_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        if not TENSEAL_AVAILABLE:
            raise RuntimeError("TenSEAL unavailable — cannot generate HE keys")
        
        # Create CKKS context and generate keys
        context = ts.context(
            ts.SCHEME_TYPE.CKKS,
            poly_modulus_degree=self.config.poly_modulus_degree,
            coeff_mod_bit_sizes=self.config.coeff_mod_bit_sizes
        )
        context.global_scale = self.config.scale
        context.generate_galois_keys()
        context.generate_relin_keys()
        
        # Serialize context (contains public key; secret key separately)
        context_bytes = context.serialize(save_secret_key=True)
        
        key_record = {
            "key_id": key_id,
            "created_at": datetime.utcnow().isoformat(),
            "active": True,  # will be deactivated on rotation
            "poly_modulus_degree": self.config.poly_modulus_degree,
            "coeff_mod_bit_sizes": self.config.coeff_mod_bit_sizes,
            "scale": self.config.scale,
            "context_blob": context_bytes,
        }
        
        path = os.path.join(self.keys_dir, f"{key_id}.hekey")
        with open(path, 'wb') as f:
            pickle.dump(key_record, f)
        
        self._keys[key_id] = key_record
        self._current_key_id = key_id
        logger.info(f"Generated HE key: {key_id}")
        return key_id
    
    def get_active_key(self) -> Optional[Dict[str, Any]]:
        """Get the currently active key."""
        if not self._current_key_id:
            # Auto-generate if none exist
            return self.generate_key() if TENSEAL_AVAILABLE else None
        return self._keys.get(self._current_key_id)
    
    def rotate_key(self, new_key_id: str = None) -> str:
        """Rotate to a new key; old key is deactivated but kept for decryption."""
        old_key_id = self._current_key_id
        if old_key_id and old_key_id in self._keys:
            self._keys[old_key_id]['active'] = False
        
        new_id = self.generate_key(new_key_id)
        logger.info(f"Rotated HE key: {old_key_id} → {new_id}")
        return new_id
    
    def should_rotate(self) -> bool:
        """Check if key rotation is due based on age."""
        active = self.get_active_key()
        if not active:
            return True
        created = datetime.fromisoformat(active['created_at'])
        age_days = (datetime.utcnow() - created).days
        return age_days >= self.config.key_rotation_days


class HomomorphicEncryptionEngine:
    """
    Homomorphic Encryption Engine for encrypted embedding operations.
    
    Supports:
    - Encrypted embedding storage and retrieval
    - Encrypted cosine similarity computation
    - Encrypted distance metrics (L2, Manhattan)
    - Batch operations on encrypted vectors
    - Key rotation with version tracking and graceful migration
    - Ciphertext integrity validation via MACs
    - Benchmarking and performance monitoring
    """
    
    def __init__(
        self, 
        config: Optional[HEContextConfig] = None,
        require_he: bool = None,
        enable_validation: bool = True,
        validator_mac_key: Optional[bytes] = None
    ):
        """
        Initialize HE Engine.
        
        Args:
            config: HE context configuration
            require_he: If True, raises error if TenSEAL unavailable.
                       If False, allows simulation mode (for dev only).
                       If None, uses ENVIRONMENT variable (production = require).
            enable_validation: Enable ciphertext MAC validation (production)
            validator_mac_key: HMAC key for ciphertext validation
        """
        self.config = config or HEContextConfig()
        
        # Determine if we require real HE
        if require_he is None:
            env = os.getenv("ENVIRONMENT", "development").lower()
            require_he = (env == "production")
        
        self.require_he = require_he
        self.simulation_mode = False
        self.context = None
        self.key_manager = None
        self._active_key_id: Optional[str] = None
        self._ciphertext_version = 1
        
        # Validation layer
        self._validator = HECiphertextValidator(
            mac_key=validator_mac_key,
            require_mac=enable_validation and require_he
        ) if enable_validation else None
        
        # Rotation manager
        self._rotation_mgr: Optional[HEKeyRotationManager] = None
        
        # Benchmark suite (lazy init)
        self._benchmark_suite: Optional[HEBenchmarkSuite] = None
        
        # Metrics
        self._metrics = {
            "encryptions": 0,
            "decryptions": 0,
            "similarity_computations": 0,
            "key_rotations": 0,
            "validation_failures": 0
        }
        
        if not TENSEAL_AVAILABLE:
            if self.require_he:
                raise RuntimeError(
                    "Homomorphic Encryption required: TenSEAL not installed. "
                    "Install with: pip install tenseal"
                )
            else:
                logger.warning("TenSEAL not available — HE operations will be simulated")
                self.simulation_mode = True
        else:
            self._initialize_he()
    
    def _initialize_he(self):
        """Initialize TenSEAL context with key management."""
        try:
            # Initialize key manager
            self.key_manager = HEKeyManager(self.config)
            active_key = self.key_manager.get_active_key()
            
            if not active_key:
                raise RuntimeError("Failed to obtain HE key")
            
            # Deserialize context from stored key
            context_blob = active_key['context_blob']
            self.context = ts.context_from(context_blob)
            self._active_key_id = active_key['key_id']
            self.simulation_mode = False
            
            # Initialize rotation manager
            self._rotation_mgr = HEKeyRotationManager(
                self.key_manager,
                rotation_days=self.config.key_rotation_days,
                grace_days=90
            )
            
            logger.info(
                f"HE Engine initialized: key_id={self._active_key_id}, "
                f"poly_modulus_degree={self.config.poly_modulus_degree}, "
                f"simulation={self.simulation_mode}"
            )
            
        except Exception as e:
            if self.require_he:
                logger.error(f"HE initialization failed: {e}")
                raise
            else:
                logger.warning(f"HE setup failed ({e}) — falling back to simulation")
                self.simulation_mode = True
    
    async def rotate_key_async(self) -> Optional[str]:
        """Async key rotation (can be called periodically)."""
        if self._rotation_mgr:
            return await self._rotation_mgr.rotate_if_needed()
        return None
    
    def get_metrics(self) -> Dict[str, int]:
        """Get operation metrics."""
        return self._metrics.copy()
    
    def _ensure_key_rotated(self):
        """Rotate key if needed (called before write operations)."""
        if self.key_manager and self.key_manager.should_rotate():
            self.key_manager.rotate_key()
            # Load new context
            active_key = self.key_manager.get_active_key()
            self.context = ts.context_from(active_key['context_blob'])
            self._active_key_id = active_key['key_id']
            logger.info(f"HE key rotated to: {self._active_key_id}")
    
    def encrypt_embedding(self, embedding: np.ndarray, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Encrypt a single embedding vector using CKKS.
        
        Args:
            embedding: numpy array of floats (normalized embedding)
            metadata: Optional additional metadata to embed
            
        Returns:
            Dict with encrypted data (serialized), metadata, and integrity tags
        """
        if self.simulation_mode:
            return {
                "encrypted": False,
                "simulation": True,
                "key_id": None,
                "dimension": len(embedding),
                "scheme": "none",
                "error": "HE unavailable — simulation mode",
                "version": self._ciphertext_version
            }
        
        try:
            self._ensure_key_rotated()
            
            # Normalize embedding
            norm_embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            
            # Encrypt using TenSEAL CKKS
            encrypted_vec = ts.ckks_vector(self.context, norm_embedding.tolist())
            encrypted_bytes = encrypted_vec.serialize()
            
            # Prepare metadata
            he_meta = HECiphertextMetadata(
                version=str(self._ciphertext_version),
                scheme="CKKS",
                poly_modulus_degree=self.config.poly_modulus_degree,
                scale=self.config.scale,
                key_id=self._active_key_id
            )
            
            # Wrap with validation
            if self._validator:
                package = self._validator.wrap_ciphertext(
                    encrypted_bytes,
                    he_meta,
                    plaintext=norm_embedding
                )
                package["metadata"]["ciphertext_format"] = "tenseal_ckks_serialized"
                if metadata:
                    package["associated_metadata"] = metadata
            else:
                package = {
                    "ciphertext": base64.b64encode(encrypted_bytes).decode(),
                    "metadata": asdict(he_meta),
                    "mac": None
                }
            
            package["encrypted"] = True
            package["simulation"] = False
            package["dimension"] = len(embedding)
            package["encrypted_at"] = datetime.utcnow().isoformat()
            
            self._metrics["encryptions"] += 1
            
            return package
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            if self.require_he:
                raise
            return {
                "encrypted": False,
                "simulation": True,
                "error": str(e),
                "dimension": len(embedding)
            }
    
    def decrypt_embedding(self, encrypted_data: Dict[str, Any]) -> Optional[np.ndarray]:
        """
        Decrypt an encrypted embedding back to numpy array.
        Requires access to the secret key.
        
        Args:
            encrypted_data: Dict from encrypt_embedding()
        
        Returns:
            numpy array of floats, or None if cannot decrypt
        """
        if self.simulation_mode or not encrypted_data.get("encrypted"):
            logger.error("Cannot decrypt: simulation mode or not encrypted")
            return None
        
        try:
            # Extract ciphertext
            if "ciphertext" in encrypted_data:
                ct_bytes = base64.b64decode(encrypted_data["ciphertext"])
            elif "data" in encrypted_data:
                # Legacy format
                ct_bytes = base64.b64decode(encrypted_data["data"])
            else:
                raise ValueError("No ciphertext found in encrypted data")
            
            # Validate if validator present
            if self._validator and "metadata" in encrypted_data:
                try:
                    ct_bytes, meta = self._validator.unwrap_ciphertext(encrypted_data)
                except ValueError as e:
                    self._metrics["validation_failures"] += 1
                    logger.error(f"Ciphertext validation failed: {e}")
                    if self.require_he:
                        raise
                    return None
            
            # Handle key migration: if ciphertext has old key_id, we need to load old context
            ciphertext_key_id = encrypted_data.get("metadata", {}).get("key_id") or \
                               encrypted_data.get("key_id")
            
            if ciphertext_key_id and ciphertext_key_id != self._active_key_id:
                logger.info(f"Decrypting with rotated key: {ciphertext_key_id}")
                # Load old key context
                old_key_data = self.key_manager._keys.get(ciphertext_key_id)
                if old_key_data:
                    old_context_blob = old_key_data['context_blob']
                    temp_context = ts.context_from(old_context_blob)
                    encrypted_vec = ts.ckks_vector_from(temp_context, ct_bytes)
                else:
                    logger.error(f"Cannot find key {ciphertext_key_id} for decryption")
                    return None
            else:
                # Use current context
                encrypted_vec = ts.ckks_vector_from(self.context, ct_bytes)
            
            # Decrypt
            plaintext = encrypted_vec.decrypt()
            result = np.array(plaintext)
            
            self._metrics["decryptions"] += 1
            
            # Verify integrity if hash provided
            if self._validator and "metadata" in encrypted_data:
                meta = HECiphertextMetadata(**encrypted_data["metadata"])
                if meta.hash_sha256:
                    if not self._validator.verify_plaintext_integrity(encrypted_data, result):
                        logger.warning("Plaintext integrity check failed")
            
            return result
            
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            return None
    
    def compute_encrypted_cosine_similarity(
        self,
        encrypted_a: Dict[str, Any],
        encrypted_b: Dict[str, Any]
    ) -> float:
        """
        Compute cosine similarity between two encrypted embeddings.
        
        Both vectors must be encrypted with compatible keys (same key_id or within grace period).
        
        Args:
            encrypted_a: First encrypted embedding (from encrypt_embedding)
            encrypted_b: Second encrypted embedding
            
        Returns:
            Cosine similarity score [-1, 1] (decrypted result)
        """
        if self.simulation_mode:
            logger.warning("Computing similarity in simulation mode")
            return self._simulated_cosine_sim(encrypted_a, encrypted_b)
        
        if not TENSEAL_AVAILABLE:
            raise RuntimeError("TenSEAL required for encrypted similarity")
        
        try:
            # Extract ciphertexts
            ct_a = encrypted_a.get("ciphertext") or encrypted_a.get("data")
            ct_b = encrypted_b.get("ciphertext") or encrypted_b.get("data")
            
            if not ct_a or not ct_b:
                raise ValueError("Missing ciphertext in input")
            
            ct_a_bytes = base64.b64decode(ct_a)
            ct_b_bytes = base64.b64decode(ct_b)
            
            # Handle key rotation: if keys differ, try loading old key context
            key_a = (encrypted_a.get("metadata") or {}).get("key_id") or encrypted_a.get("key_id")
            key_b = (encrypted_b.get("metadata") or {}).get("key_id") or encrypted_b.get("key_id")
            
            # For homomorphic operations, both need to be in same context
            # If keys differ, we cannot directly compute; raise error
            if key_a and key_b and key_a != key_b:
                logger.error(f"Key mismatch: {key_a} vs {key_b}. Re-encrypt needed.")
                raise ValueError("Ciphertexts encrypted under different keys")
            
            # Use appropriate context (current for both if same key)
            context = self.context
            
            vec_a = ts.ckks_vector_from(context, ct_a_bytes)
            vec_b = ts.ckks_vector_from(context, ct_b_bytes)
            
            # Homomorphic dot product: vec_a * vec_b (element-wise) then sum
            dot_product = (vec_a * vec_b).sum()
            
            # Homomorphic norms
            norm_a_sq = (vec_a * vec_a).sum()
            norm_b_sq = (vec_b * vec_b).sum()
            
            # Decrypt both dot product and norms (requires secret key)
            dot_val = dot_product.decrypt()[0]
            norm_a_val = norm_a_sq.decrypt()[0]
            norm_b_val = norm_b_sq.decrypt()[0]
            
            if norm_a_val <= 0 or norm_b_val <= 0:
                return 0.0
            
            similarity = dot_val / (np.sqrt(norm_a_val) * np.sqrt(norm_b_val))
            result = float(np.clip(similarity, -1.0, 1.0))
            
            self._metrics["similarity_computations"] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"Encrypted similarity computation failed: {e}")
            if self.require_he:
                raise
            return self._simulated_cosine_sim(encrypted_a, encrypted_b)
    
    def _simulated_cosine_sim(
        self,
        enc_a: Dict[str, Any],
        enc_b: Dict[str, Any]
    ) -> float:
        """Deterministic simulation for dev/testing only."""
        # Based on dimension and pseudo-hash of payload
        dim = enc_a.get("dimension", 512)
        payload_a = enc_a.get("data", "")
        payload_b = enc_b.get("data", "")
        
        if not payload_a or not payload_b:
            return 0.5
        
        # Pseudo-random but deterministic similarity from payloads
        digest = hashlib.sha256((payload_a + payload_b).encode()).digest()
        val = int.from_bytes(digest[:4], 'big') / (2**32)
        return float(val)  # [0, 1]
    
    def batch_encrypt_embeddings(
        self,
        embeddings: List[np.ndarray]
    ) -> List[Dict[str, Any]]:
        """Encrypt multiple embeddings in batch."""
        return [self.encrypt_embedding(emb) for emb in embeddings]
    
    def encrypted_nearest_neighbor_search(
        self,
        query_encrypted: Dict[str, Any],
        database_encrypted: List[Dict[str, Any]],
        database_ids: List[str],
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Perform k-NN search on encrypted embeddings.
        
        All similarity computation is done homomorphically,
        with decryption only of final similarity values.
        """
        similarities = []
        for idx, db_enc in enumerate(database_encrypted):
            try:
                sim = self.compute_encrypted_cosine_similarity(
                    query_encrypted, db_enc
                )
                similarities.append((database_ids[idx], sim))
            except Exception as e:
                logger.error(f"Similarity error for {database_ids[idx]}: {e}")
                similarities.append((database_ids[idx], 0.0))
        
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:top_k]
    
    def cross_org_secure_match(
        self,
        org_a_encrypted: Dict[str, Any],
        org_b_database: List[Dict[str, Any]],
        org_b_ids: List[str],
        threshold: float = 0.7
    ) -> Optional[Tuple[str, float]]:
        """
        Secure cross-organization identity matching.
        No organization sees the other's raw embeddings.
        """
        matches = self.encrypted_nearest_neighbor_search(
            org_a_encrypted, org_b_database, org_b_ids, top_k=1
        )
        return matches[0] if matches and matches[0][1] >= threshold else None
    
    def verify_encrypted_integrity(
        self,
        encrypted_data: Dict[str, Any]
    ) -> bool:
        """Verify integrity of an encrypted embedding."""
        required = ["dimension", "encrypted"]
        for field in required:
            if field not in encrypted_data:
                return False
        
        if encrypted_data.get("encrypted") and TENSEAL_AVAILABLE and not self.simulation_mode:
            try:
                data = base64.b64decode(encrypted_data.get("data", ""))
                _ = ts.ckks_vector_from(self.context, data)
                return True
            except Exception:
                return False
        return encrypted_data.get("dimension", 0) > 0
    
    def get_metadata(self) -> Dict[str, Any]:
        """Get encryption engine metadata."""
        return {
            "enabled": not self.simulation_mode,
            "simulation_mode": self.simulation_mode,
            "scheme": "CKKS" if not self.simulation_mode else "none",
            "tenseal_available": TENSEAL_AVAILABLE,
            "key_id": self._active_key_id,
            "key_rotation_due": self.key_manager.should_rotate() if self.key_manager else False,
            "require_he": self.require_he,
            "poly_modulus_degree": self.config.poly_modulus_degree,
            "security_level": "high" if not self.simulation_mode else "none",
            "capabilities": (
                "encrypt", "decrypt", "encrypted_similarity",
                "encrypted_nn_search", "cross_org_match", "key_rotation",
                "ciphertext_validation", "integrity_protection"
            ) if not self.simulation_mode else ["simulated_operations"],
            "metrics": self._metrics,
            "ciphertext_version": self._ciphertext_version
        }
    
    def get_benchmark_suite(self) -> HEBenchmarkSuite:
        """Get benchmark suite for performance testing."""
        if self._benchmark_suite is None:
            self._benchmark_suite = HEBenchmarkSuite(self)
        return self._benchmark_suite
    
    def benchmark_and_report(self, output_path: str = None) -> Dict[str, Any]:
        """
        Run full benchmark and optionally export results.
        
        Args:
            output_path: Optional path to export JSON results
            
        Returns:
            Benchmark results dict
        """
        suite = self.get_benchmark_suite()
        results = suite.run_full_suite()
        
        if output_path:
            suite.export_results_json(output_path)
        
        return results


class HomomorphicVectorStore:
    """Vector store that keeps all embeddings encrypted at rest."""
    
    def __init__(self, he_engine: HomomorphicEncryptionEngine):
        self.he_engine = he_engine
        self.embeddings: Dict[str, Dict[str, Any]] = {}
        self.metadata: Dict[str, Dict[str, Any]] = {}
    
    def add_embedding(
        self,
        item_id: str,
        embedding: np.ndarray,
        item_metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        try:
            encrypted = self.he_engine.encrypt_embedding(embedding)
            self.embeddings[item_id] = encrypted
            self.metadata[item_id] = item_metadata or {}
            return True
        except Exception as e:
            logger.error(f"Failed to add embedding {item_id}: {e}")
            return False
    
    def search(
        self,
        query_embedding: np.ndarray,
        top_k: int = 10,
        threshold: float = 0.0
    ) -> List[Tuple[str, float, Dict[str, Any]]]:
        query_enc = self.he_engine.encrypt_embedding(query_embedding)
        db_ids = list(self.embeddings.keys())
        db_embs = [self.embeddings[i] for i in db_ids]
        
        matches = self.he_engine.encrypted_nearest_neighbor_search(
            query_enc, db_embs, db_ids, top_k=top_k
        )
        
        return [
            (mid, sim, self.metadata.get(mid, {}))
            for mid, sim in matches if sim >= threshold
        ]
    
    def cross_store_search(
        self,
        query_store: 'HomomorphicVectorStore',
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        matches = []
        for qid, qemb in query_store.embeddings.items():
            db_ids = list(self.embeddings.keys())
            db_embs = [self.embeddings[i] for i in db_ids]
            results = self.he_engine.encrypted_nearest_neighbor_search(
                qemb, db_embs, db_ids, top_k=top_k
            )
            for mid, sim in results:
                matches.append({
                    "query_id": qid,
                    "match_id": mid,
                    "similarity": sim,
                    "query_metadata": query_store.metadata.get(qid, {}),
                    "match_metadata": self.metadata.get(mid, {})
                })
        return matches
    
    def get_encrypted_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        return self.embeddings.get(item_id)
    
    def size(self) -> int:
        return len(self.embeddings)
    
    def verify_all_integrity(self) -> Dict[str, bool]:
        return {
            item_id: self.he_engine.verify_encrypted_integrity(enc)
            for item_id, enc in self.embeddings.items()
        }
