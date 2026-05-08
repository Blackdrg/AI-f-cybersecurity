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
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np

try:
    import tenseal as ts
    TENSEAL_AVAILABLE = True
except ImportError:
    TENSEAL_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class HEContextConfig:
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
    - Key rotation with versioning
    """
    
    def __init__(
        self, 
        config: Optional[HEContextConfig] = None,
        require_he: bool = None
    ):
        """
        Initialize HE Engine.
        
        Args:
            config: HE context configuration
            require_he: If True, raises error if TenSEAL unavailable.
                       If False, allows simulation mode (for dev only).
                       If None, uses ENVIRONMENT variable (production = require).
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
            
            logger.info(
                f"HE Engine initialized: key_id={self._active_key_id}, "
                f"poly_modulus_degree={self.config.poly_modulus_degree}"
            )
            
            # Check for key rotation
            if self.key_manager.should_rotate():
                logger.info("HE key rotation due — scheduling rotation")
                # Rotation happens on next write (key rotation is async-safe)
                
        except Exception as e:
            if self.require_he:
                logger.error(f"HE initialization failed: {e}")
                raise
            else:
                logger.warning(f"HE setup failed ({e}) — falling back to simulation")
                self.simulation_mode = True
    
    def _ensure_key_rotated(self):
        """Rotate key if needed (called before write operations)."""
        if self.key_manager and self.key_manager.should_rotate():
            self.key_manager.rotate_key()
            # Load new context
            active_key = self.key_manager.get_active_key()
            self.context = ts.context_from(active_key['context_blob'])
            self._active_key_id = active_key['key_id']
            logger.info(f"HE key rotated to: {self._active_key_id}")
    
    def encrypt_embedding(self, embedding: np.ndarray) -> Dict[str, Any]:
        """
        Encrypt a single embedding vector using CKKS.
        
        Args:
            embedding: numpy array of floats (normalized embedding)
        
        Returns:
            Dict with encrypted data (serialized) and metadata
        """
        if self.simulation_mode:
            return {
                "encrypted": False,
                "simulation": True,
                "key_id": None,
                "dimension": len(embedding),
                "scheme": "none",
                "error": "HE unavailable — simulation mode"
            }
        
        try:
            self._ensure_key_rotated()
            
            # Normalize embedding
            norm_embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
            
            # Encrypt using TenSEAL CKKS
            encrypted_vec = ts.ckks_vector(self.context, norm_embedding.tolist())
            encrypted_bytes = encrypted_vec.serialize()
            
            return {
                "encrypted": True,
                "simulation": False,
                "data": base64.b64encode(encrypted_bytes).decode(),
                "dimension": len(embedding),
                "scheme": "CKKS",
                "poly_modulus_degree": self.config.poly_modulus_degree,
                "scale": self.config.scale,
                "key_id": self._active_key_id,
                "encrypted_at": datetime.utcnow().isoformat()
            }
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
            vec_bytes = base64.b64decode(encrypted_data["data"])
            encrypted_vec = ts.ckks_vector_from(self.context, vec_bytes)
            plaintext = encrypted_vec.decrypt()
            return np.array(plaintext)
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
        
        Both vectors must be encrypted with compatible keys.
        
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
            # Deserialize encrypted vectors
            vec_a_bytes = base64.b64decode(encrypted_a["data"])
            vec_b_bytes = base64.b64decode(encrypted_b["data"])
            
            vec_a = ts.ckks_vector_from(self.context, vec_a_bytes)
            vec_b = ts.ckks_vector_from(self.context, vec_b_bytes)
            
            # Homomorphic dot product: vec_a * vec_b (element-wise) then sum
            dot_product = (vec_a * vec_b).sum()
            
            # Homomorphic norms: (vec_a * vec_a).sum(), same for b
            norm_a_sq = (vec_a * vec_a).sum()
            norm_b_sq = (vec_b * vec_b).sum()
            
            # Decrypt both dot product and norms (requires secret key)
            dot_val = dot_product.decrypt()[0]
            norm_a_val = norm_a_sq.decrypt()[0]
            norm_b_val = norm_b_sq.decrypt()[0]
            
            if norm_a_val <= 0 or norm_b_val <= 0:
                return 0.0
            
            similarity = dot_val / (np.sqrt(norm_a_val) * np.sqrt(norm_b_val))
            return float(np.clip(similarity, -1.0, 1.0))
            
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
            "require_he": self.require_he,
            "poly_modulus_degree": self.config.poly_modulus_degree,
            "security_level": "high" if not self.simulation_mode else "none",
            "capabilities": (
                "encrypt", "decrypt", "encrypted_similarity",
                "encrypted_nn_search", "cross_org_match"
            ) if not self.simulation_mode else ["simulated_operations"]
        }


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
