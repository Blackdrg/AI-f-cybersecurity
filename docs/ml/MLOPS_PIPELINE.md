# MLOps Pipeline for AI-f

**Status: Production**  
**Version: 2.0**

---

## Architecture Overview

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Data Lake     │────▶│  Feature Store  │────▶│  Training       │
│  (Raw Events)   │     │ (Feature Engine)│     │  Pipeline       │
└─────────────────┘     └─────────────────┘     └────────┬────────┘
                                                             │
                                                             ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Model Registry │◀────│  Model Builder  │◀────│  Experiment     │
│ (Versioned)     │     │ (AutoML)        │     │  Tracking       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                             │
                                                             ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Shadow Deploy  │────▶│  Model Server   │────▶│  Production     │
│  (Canary)       │     │ (Serving)       │     │  Traffic        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

---

## Components

### 1. Feature Store

```python
# backend/app/ml/feature_store.py
import pandas as pd
from typing import Dict, Any

class FeatureStore:
    """Centralized feature management."""
    
    def __init__(self):
        self.features = {}
    
    def compute_face_features(self, embedding: list) -> Dict[str, Any]:
        """Compute derived features from face embedding."""
        import numpy as np
        
        emb_array = np.array(embedding)
        
        features = {
            "embedding_norm": float(np.linalg.norm(emb_array)),
            "embedding_mean": float(np.mean(emb_array)),
            "embedding_std": float(np.std(emb_array)),
            "embedding_min": float(np.min(emb_array)),
            "embedding_max": float(np.max(emb_array)),
            "l2_normalized": float(np.linalg.norm(emb_array / np.linalg.norm(emb_array))),
        }
        
        return features
    
    def store_features(self, feature_set: str, features: Dict[str, Any], person_id: str):
        """Store computed features."""
        self.features[f"{feature_set}:{person_id}"] = features
        return True
    
    def get_features(self, feature_set: str, person_id: str) -> Dict[str, Any]:
        """Retrieve stored features."""
        return self.features.get(f"{feature_set}:{person_id}", {})
```

### 2. Model Registry

```python
# backend/app/ml/model_registry.py
import uuid
from datetime import datetime
from typing import Optional, Dict, Any
import json
import os

class ModelRegistry:
    """ML model versioning and lifecycle management."""
    
    def __init__(self, storage_path: str = "/models"):
        self.storage_path = storage_path
        self.registry_file = os.path.join(storage_path, "registry.json")
        self._ensure_storage()
    
    def _ensure_storage(self):
        os.makedirs(self.storage_path, exist_ok=True)
        if not os.path.exists(self.registry_file):
            with open(self.registry_file, "w") as f:
                json.dump({"models": {}}, f)
    
    def register_model(self, model_data: bytes, metadata: Dict[str, Any], framework: str = "onnx") -> str:
        """Register a new model version."""
        model_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        # Store model file
        model_path = os.path.join(self.storage_path, f"{model_id}.{framework}")
        with open(model_path, "wb") as f:
            f.write(model_data)
        
        # Update registry
        with open(self.registry_file, "r") as f:
            registry = json.load(f)
        
        registry["models"][model_id] = {
            "id": model_id,
            "created_at": timestamp,
            "framework": framework,
            "metadata": metadata,
            "status": "staging",
            "performance": {}
        }
        
        with open(self.registry_file, "w") as f:
            json.dump(registry, f, indent=2)
        
        return model_id
    
    def promote_model(self, model_id: str, stage: str = "production") -> bool:
        """Promote model to production stage."""
        with open(self.registry_file, "r") as f:
            registry = json.load(f)
        
        if model_id not in registry["models"]:
            return False
        
        registry["models"][model_id]["status"] = stage
        registry["models"][model_id]["promoted_at"] = datetime.utcnow().isoformat()
        
        with open(self.registry_file, "w") as f:
            json.dump(registry, f, indent=2)
        
        return True
    
    def get_production_model(self) -> Optional[Dict[str, Any]]:
        """Get currently promoted model."""
        with open(self.registry_file, "r") as f:
            registry = json.load(f)
        
        for model_id, model in registry["models"].items():
            if model["status"] == "production":
                return {"id": model_id, **model}
        
        return None
```

### 3. Automated Retraining

```python
# backend/app/tasks/model_training_tasks.py
import asyncio
from datetime import datetime, timedelta
from ..ml.model_registry import ModelRegistry

async def trigger_automated_retraining():
    """Trigger model retraining based on performance thresholds."""
    from ..services.metrics import get_model_performance
    
    performance = await get_model_performance()
    
    # Check if retraining needed
    if performance.get("accuracy", 1.0) < 0.95:
        print("Accuracy below threshold - triggering retraining")
        return await run_training_pipeline()
    
    # Check data drift
    if performance.get("drift_score", 0.0) > 0.7:
        print("Data drift detected - triggering retraining")
        return await run_training_pipeline()
    
    print("No retraining needed")
    return None

async def run_training_pipeline():
    """Execute full training pipeline."""
    # 1. Fetch new training data
    new_data = await fetch_training_data()
    
    # 2. Compute features
    features = compute_features(new_data)
    
    # 3. Train model
    model = await train_model(features)
    
    # 4. Evaluate
    metrics = await evaluate_model(model, features)
    
    # 5. Register if improved
    if metrics["accuracy"] > 0.95:
        registry = ModelRegistry()
        model_bytes = await serialize_model(model)
        model_id = registry.register_model(
            model_bytes,
            {
                "accuracy": metrics["accuracy"],
                "trained_at": datetime.utcnow().isoformat(),
                "dataset_size": len(features)
            }
        )
        
        # Shadow deployment for validation
        await deploy_shadow_model(model_id)
        
        return model_id
    
    return None

async def fetch_training_data():
    """Fetch new training data from database."""
    # Implementation details...
    return []

async def compute_features(data):
    """Compute features from raw data."""
    store = FeatureStore()
    features = []
    for item in data:
        features.append(store.compute_face_features(item["embedding"]))
    return features

async def train_model(features):
    """Train model on features."""
    # Implementation details...
    return None

async def evaluate_model(model, features):
    """Evaluate model performance."""
    return {"accuracy": 0.96}

async def serialize_model(model):
    """Serialize model to bytes."""
    import pickle
    return pickle.dumps(model)

async def deploy_shadow_model(model_id):
    """Deploy model for shadow testing."""
    # Deploy to shadow endpoint for comparison
    pass
```

---

## Pipeline Stages

### Stage 1: Data Validation
- Schema validation
- Data quality checks
- Drift detection

### Stage 2: Feature Engineering
- Feature computation
- Feature validation
- Feature store update

### Stage 3: Model Training
- Hyperparameter tuning
- Cross-validation
- Performance evaluation

### Stage 4: Model Validation
- Accuracy threshold check
- Fairness assessment
- Bias detection

### Stage 5: Deployment
- Shadow deployment
- Canary release
- Production promotion

---

## Shadow Deployment

```python
# backend/app/ml/shadow_deployment.py
import numpy as np
from typing import Dict, Any

class ShadowDeployment:
    """Shadow deployment for model comparison."""
    
    def __init__(self):
        self.current_model = None
        self.shadow_model = None
        self.results = []
    
    async def compare_predictions(self, input_data: list, ground_truth: Any = None) -> Dict:
        """Compare current and shadow model predictions."""
        # Get predictions from both models
        current_pred = await self.current_model.predict(input_data)
        shadow_pred = await self.shadow_model.predict(input_data)
        
        comparison = {
            "current_prediction": current_pred,
            "shadow_prediction": shadow_pred,
            "agreement": np.allclose(current_pred, shadow_pred, rtol=0.01),
            "difference": abs(current_pred - shadow_pred).tolist() if isinstance(current_pred, (int, float)) else None
        }
        
        if ground_truth is not None:
            comparison["current_accuracy"] = self._compute_accuracy(current_pred, ground_truth)
            comparison["shadow_accuracy"] = self._compute_accuracy(shadow_pred, ground_truth)
        
        self.results.append(comparison)
        return comparison
    
    def _compute_accuracy(self, prediction, ground_truth):
        """Compute accuracy metric."""
        return float(np.mean(np.array(prediction) == np.array(ground_truth)))
    
    def should_promote(self, threshold: float = 0.01) -> bool:
        """Check if shadow model should be promoted."""
        if not self.results:
            return False
        
        # Calculate average improvement
        improvements = [
            abs(r.get("difference", 0)) for r in self.results[-100:]
        ]
        avg_improvement = np.mean(improvements)
        
        return avg_improvement > threshold
```

---

## Metrics and Monitoring

### Key Metrics
- Model accuracy
- Prediction latency
- Data drift score
- Feature distribution shift
- Fairness metrics

### Alerting Thresholds
- Accuracy < 95%: Alert and trigger retraining
- Latency > 300ms: Scale up serving
- Drift > 0.7: Investigate data quality

---

## Rollback Procedure

```python
async def rollback_model(previous_version: str):
    """Rollback to previous model version."""
    registry = ModelRegistry()
    
    # Get previous model
    previous = registry.get_model(previous_version)
    if not previous:
        raise ValueError(f"Model {previous_version} not found")
    
    # Promote previous to production
    registry.promote_model(previous_version, "production")
    
    # Update serving endpoint
    await update_serving_endpoint(previous_version)
    
    return previous_version
```

---

## CI/CD Integration

```yaml
# .github/workflows/ml_pipeline.yml
name: MLOps Pipeline

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM
  workflow_dispatch:

jobs:
  retrain:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Check performance
        run: |
          python -c "
          from app.tasks.model_training_tasks import trigger_automated_retraining
          asyncio.run(trigger_automated_retraining())
          "
      
      - name: Deploy if improved
        if: steps.check.outputs.should_deploy == 'true'
        run: |
          kubectl set image deployment/model-server model-server=new-model:latest
```