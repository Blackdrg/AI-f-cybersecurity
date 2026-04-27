"""
Model Registry Service
Centralized storage, versioning, and distribution of ML models
"""
import os
import json
import hashlib
import shutil
from typing import Dict, Optional, List, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import structlog
from ..db.db_client import get_db

logger = logging.getLogger(__name__)


@dataclass
class ModelMetadata:
    """Model registry entry metadata"""
    model_id: str
    name: str
    version: str
    framework: str  # pytorch, onnx, tensorflow
    architecture: str
    input_shape: List[int]
    output_dim: int
    description: str
    training_dataset: str
    metrics: Dict[str, float]
    size_bytes: int
    checksum: str  # SHA256
    signature: Optional[str] = None  # Optional digital signature
    created_at: str
    uploaded_by: str
    status: str = "staging"  # staging, production, deprecated
    tags: List[str] = None
    download_count: int = 0
    min_requirements: Dict[str, Any] = None  # hardware requirements
    
    def to_dict(self):
        return asdict(self)


class ModelRegistry:
    """
    Persistent model registry with database + filesystem storage.
    Supports versioning, promotion, OTA distribution.
    """
    
    def __init__(self, storage_path: str = "/app/models/registry"):
        self.storage_path = storage_path
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """Ensure storage directories exist"""
        os.makedirs(self.storage_path, exist_ok=True)
        os.makedirs(os.path.join(self.storage_path, "models"), exist_ok=True)
        os.makedirs(os.path.join(self.storage_path, "metadata"), exist_ok=True)
    
    async def register_model(self, 
                             name: str,
                             version: str,
                             model_path: str,
                             framework: str,
                             architecture: str,
                             input_shape: List[int],
                             output_dim: int,
                             description: str,
                             training_dataset: str,
                             metrics: Dict[str, float],
                             uploaded_by: str,
                             tags: List[str] = None,
                             min_requirements: Dict = None) -> ModelMetadata:
        """
        Register a new model version.
        
        Args:
            model_path: Path to model file (will be copied to registry)
            metrics: Dict with accuracy, loss, etc.
        
        Returns:
            ModelMetadata instance
        """
        # Generate model_id from name + version
        model_id = f"{name}_{version}"
        
        # Compute checksum
        sha256 = hashlib.sha256()
        with open(model_path, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        checksum = sha256.hexdigest()
        
        # Get file size
        size_bytes = os.path.getsize(model_path)
        
        # Copy model to registry storage
        dest_path = os.path.join(self.storage_path, "models", f"{model_id}.{framework}")
        shutil.copy2(model_path, dest_path)
        
        # Create metadata
        metadata = ModelMetadata(
            model_id=model_id,
            name=name,
            version=version,
            framework=framework,
            architecture=architecture,
            input_shape=input_shape,
            output_dim=output_dim,
            description=description,
            training_dataset=training_dataset,
            metrics=metrics,
            size_bytes=size_bytes,
            checksum=checksum,
            created_at=datetime.utcnow().isoformat(),
            uploaded_by=uploaded_by,
            status="staging",
            tags=tags or [],
            min_requirements=min_requirements or {}
        )
        
        # Store in DB
        db = await get_db()
        await db.store_model_metadata(metadata)
        
        logger.info(f"Registered model {model_id} ({size_bytes} bytes, checksum {checksum[:8]})")
        return metadata
    
    async def get_model_info(self, model_id: str) -> Optional[ModelMetadata]:
        """Get model metadata by ID"""
        db = await get_db()
        row = await db.get_model_metadata(model_id)
        if row:
            return ModelMetadata(**row)
        return None
    
    async def list_models(self, name: str = None, status: str = None) -> List[ModelMetadata]:
        """List all models with optional filters"""
        db = await get_db()
        rows = await db.list_model_metadata(name_filter=name, status=status)
        return [ModelMetadata(**row) for row in rows]
    
    async def promote_to_production(self, model_id: str) -> bool:
        """Promote a model version to production"""
        db = await get_db()
        # Demote current production if exists
        await db.update_model_status_by_name(
            name=model_id.split('_')[0],  # base name
            status="deprecated", 
            exclude_version=model_id
        )
        # Promote new
        success = await db.update_model_status(model_id, "production")
        if success:
            logger.info(f"Promoted {model_id} to production")
        return success
    
    async def get_production_model(self, name: str) -> Optional[ModelMetadata]:
        """Get current production model by name"""
        db = await get_db()
        row = await db.get_production_model(name)
        return ModelMetadata(**row) if row else None
    
    async def download_model(self, model_id: str, dest_path: str = None) -> str:
        """
        Download model file (used by OTA updates).
        Returns path to downloaded file.
        """
        meta = await self.get_model_info(model_id)
        if not meta:
            raise FileNotFoundError(f"Model {model_id} not found")
        
        src = os.path.join(self.storage_path, "models", f"{model_id}.{meta.framework}")
        if not os.path.exists(src):
            raise FileNotFoundError(f"Model file missing: {src}")
        
        # Verify checksum
        sha256 = hashlib.sha256()
        with open(src, 'rb') as f:
            while chunk := f.read(8192):
                sha256.update(chunk)
        if sha256.hexdigest() != meta.checksum:
            raise ValueError("Checksum verification failed")
        
        if dest_path:
            shutil.copy2(src, dest_path)
            # Increment download count
            db = await get_db()
            await db.increment_model_downloads(model_id)
            return dest_path
        return src
    
    async def delete_model(self, model_id: str) -> bool:
        """Delete a model version (only if not production)"""
        meta = await self.get_model_info(model_id)
        if meta and meta.status == "production":
            raise ValueError("Cannot delete production model")
        
        db = await get_db()
        success = await db.delete_model_metadata(model_id)
        if success:
            # Remove file
            model_file = os.path.join(self.storage_path, "models", f"{model_id}.{meta.framework}")
            if os.path.exists(model_file):
                os.remove(model_file)
            logger.info(f"Deleted model {model_id}")
        return success
    
    async def get_model_sources(self) -> Dict[str, List[str]]:
        """
        Return model download sources (mirrors) for resilience.
        Used by edge devices for failover.
        """
        db = await get_db()
        mirrors = await db.get_config("model_mirrors", default=[])
        primary = os.getenv("MODEL_REGISTRY_URL", "http://localhost:8000")
        return {
            "primary": [primary],
            "mirrors": mirrors,
            "checksum": "sha256"
        }


# Global registry
model_registry = ModelRegistry()
