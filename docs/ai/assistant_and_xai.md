# AI Assistant & Explainable AI (XAI) Endpoints

## Overview

AI-f provides AI-powered assistance for operators and explainable AI
breakdowns for every recognition decision.

---

## 1. AI Assistant Query

**Endpoint:** `POST /api/ai/assistant`  
**Auth:** Required (any authenticated user)

### Purpose

Natural language interface to ask questions about:
- Face recognition technology
- Compliance regulations (GDPR, BIPA)
- System configuration
- Troubleshooting
- Best practices

### Request

```json
{
  "query": "How does age affect recognition accuracy?",
  "context": {
    "use_case": "security",
    "jurisdiction": "US"
  }
}
```

### Response

```json
{
  "query": "How does age affect recognition accuracy?",
  "response": "Face recognition accuracy degrades approximately 3-5% over 5-year spans due to natural aging. For subjects over 65, degradation can reach 8-12%. We recommend re-enrollment every 3 years or when visible changes occur. Our model uses age-invariant features, but extreme aging (50+ years) still challenges even state-of-the-art systems.",
  "model_used": "gpt-4",
  "sources": [
    "docs/faq/aging.md",
    "research/FaceRecognitionAcrossTheAges.pdf"
  ],
  "confidence": 0.92,
  "tokens_used": 156
}
```

### Model Selection

| User Tier | Model | Context Window | Notes |
|-----------|-------|----------------|-------|
| Free / Pro | GPT-3.5 Turbo | 4K | General assistance |
| Enterprise | GPT-4 | 8K | Technical depth, multi-lingual |
| Premium (daredevil0101a@gmail.com) | GPT-4 | 8K | Expert-level, code examples |

### Usage Limits

| Tier | Queries / month | Rate limit |
|------|-----------------|------------|
| Free | 50 | 10/min |
| Pro | 500 | 30/min |
| Enterprise | Unlimited | 100/min |

### Example Queries

```
"Configure MFA for my organization"
"What's the difference between GDPR and CCPA?"
"My camera isn't connecting — give me troubleshooting steps"
"Show me the ZKP verification code"
"Optimize my deployment for 10,000 RPS"
```

---

## 2. Explanation Retrieval

**Endpoint:** `GET /api/explanations/{explanation_id}`  
**Auth:** Required (VIEW_EXPLANATIONS permission)

### Purpose

Retrieve XAI (Explainable AI) breakdown for a specific recognition event.
Shows which facial features contributed most to the match decision.

**Use cases:**
- Audit why a false positive occurred
- Debug recognition failures
- Satisfy regulatory "right to explanation" (GDPR Art. 22)
- Improve model transparency

### Request

```
GET /api/explanations/exp_abc123def456
Authorization: Bearer <token>
```

### Response

```json
{
  "explanation_id": "exp_abc123def456",
  "person_id": "pers_001",
  "event_id": "event_xyz789",
  "recognition_id": "rec_abc123",
  "method": "SHAP",                  // XAI method used
  "timestamp": "2026-04-28T12:00:00Z",
  
  "feature_importance": [
    {
      "feature": "left_eye_region",
      "importance": 0.234,
      "contribution": "positive",
      "heatmap": "base64-encoded-saliency-map-if-requested"
    },
    {
      "feature": "nose_bridge",
      "importance": 0.187,
      "contribution": "positive"
    },
    {
      "feature": "mouth_corners",
      "importance": 0.089,
      "contribution": "slightly_negative"
    },
    {
      "feature": "forehead",
      "importance": 0.032,
      "contribution": "negative"
    }
  ],
  
  "decision_threshold": 0.6,
  "confidence_score": 0.947,
  "decision": "match",
  
  "alternative_matches": [
    {
      "person_id": "pers_002",
      "name": "Jane Smith",
      "score": 0.823,
      "top_opposing_features": ["jawline", "cheekbones"]
    }
  ],
  
  "verification_zkp": {
    "proof_type": "schnorr_decision_correctness",
    "statement_hash": "sha256:...",
    "verified": true,
    "verified_at": "2026-04-28T12:05:00Z"
  },
  
  "model_version": "v2.1.0"
}
```

### XAI Methods

| Method | Description | When used |
|--------|-------------|-----------|
| **SHAP (SHapley Additive exPlanations)** | Game theory-based feature importance | Default — most accurate |
| **Integrated Gradients** | Path attribution from baseline | For image-based gradient analysis |
| **LIME (Local Interpretable Model-agnostic Explanations)** | Perturbation-based local surrogate | Fallback if SHAP unavailable |

**Configuration:** Set in `policy_engine` or per-request via `?method=shap` query param.

---

## 3. Batch XAI Analysis

**Endpoint:** `POST /api/explanations/batch`  
**Auth:** Required (admin only)

Generate XAI for multiple recognition events (e.g., for bias audit).

**Request:**
```json
{
  "event_ids": ["event_1", "event_2", "event_3"],
  "method": "shap",
  "aggregate": true
}
```

**Response:**
```json
{
  "explanations": [ /* array of Explanation objects */ ],
  "aggregate_stats": {
    "avg_top_feature_importance": 0.312,
    "feature_importance_by_demographic": {
      "male": {"eyes": 0.28, "nose": 0.22, ...},
      "female": {"eyes": 0.31, "nose": 0.19, ...}
    }
  }
}
```

---

## 4. Model Card & Documentation

**Endpoint:** `GET /api/models/{model_name}/card`  
**Auth:** Optional (public for transparency)

Retrieve model documentation card (following Google's Model Card template):

```json
{
  "model_name": "face-embedder-arcface-r100",
  "version": "v2.1.0",
  "description": "ArcFace ResNet-100 face recognition embedding model",
  "intended_use": "Biometric identity verification",
  "training_data": "MS1M-ArcFace dataset (5.8M images, 85K identities)",
  "performance": {
    "LFW_accuracy": 0.9983,
    "IJB-C_FAR_0.001": 0.997
  },
  "limitations": [
    "Degradation with age > 5 years",
    "Poor performance with extreme lighting",
    "Not robust to adversarial perturbations"
  ],
  "fairness_metrics": {
    "demographic_parity_difference": 0.018,
    "equalized_odds_difference": 0.012
  }
}
```

---

## Technical Architecture

### AI Assistant Flow

```
User query → LLM Provider (OpenAI/Anthropic) → Response
                ↑
           System prompt:
           "You are AI-f assistant specializing in face recognition..."
                ↓
        Context injection:
        - Current system metrics
        - Relevant docs (RAG)
        - User's org tier
```

**Provider abstraction:** `app/providers/llm_provider.py`

### XAI Generation

```
Recognition event
      ↓
Load model & input face embedding + reference embeddings
      ↓
Run XAI method (SHAP)
      ↓
Compute gradient/attribution per pixel/feature
      ↓
Project to original image space
      ↓
Store in explanations table
      ↓
Return to user / embed in audit log
```

**Storage:** `explanations` table (structured + optional heatmap image in S3)

---

## API Rate Limits

| Endpoint | Free | Pro | Enterprise |
|----------|------|-----|------------|
| `POST /api/ai/assistant` | 10/mo | 100/mo | 1000/mo |
| `GET /api/explanations/{id}` | 20/mo | 200/mo | 2000/mo |
| `POST /api/explanations/batch` | N/A | 5/batch | 50/batch |

---

## Audit Trail

All AI assistant queries and XAI retrievals are logged:

```sql
INSERT INTO ai_assistant_logs (
    user_id, query, response_preview, model_used, tokens, timestamp
) VALUES (...)
```

Used for:
- Cost tracking (LLM API spend)
- Quality assurance (bad answers monitoring)
- Compliance (LLM output retention)

---

## Troubleshooting

### "AI assistant unavailable"

**Cause:** `OPENAI_API_KEY` not set or quota exceeded.

**Fix:** Configure OpenAI API key in environment.

---

### "XAI generation failed"

**Cause:** Model file missing or GPU out of memory.

**Fix:** Verify model loaded (`GET /api/health`), increase `ORT_GPU_MEMORY_LIMIT`.

---

### Slow XAI response (> 5 seconds)

**Cause:** XAI methods compute-intensive (especially SHAP on 512-d embeddings).

**Mitigation:** Use integrated gradients (faster), enable caching (`/api/explanations/{id}` memoized), batch requests.

---

## Future Roadmap

- **Multi-modal XAI:** Explain which modality (face, voice, gait) contributed most
- **Counterfactual explanations:** "What would need to change to get a different result?"
- **Personalized explanations:** Tailor technical depth to user role (operator vs auditor)
- **Visual heatmaps:** Overlay saliency map on original face image
- **Batch fairness analysis:** Compare feature importance across demographic groups

---

## References

1. SHAP: Lundberg, S. M., & Lee, S. I. (2017). "A unified approach to interpreting model predictions." NIPS.
2. Integrated Gradients: Sundararajan, M., et al. (2017). "Axiomatic attribution for deep networks." ICML.
3. LIME: Ribeiro, M. T., et al. (2016). ""Why should I trust you?" Explaining the predictions of any classifier." KDD.
