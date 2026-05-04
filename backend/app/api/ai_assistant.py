from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Dict, Any
import logging
from app.providers import get_llm_provider
from app.middleware.auth import get_current_user
from app.db.db_client import get_db
from app.services.redis_client import get_redis
from datetime import datetime

router = APIRouter(tags=["ai_assistant"])
logger = logging.getLogger(__name__)

class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    model: str = "gpt-4o-mini"
    max_tokens: int = 500
    temperature: float = 0.7

class ChatResponse(BaseModel):
    response: str
    usage: Dict[str, int]
    status: str

@router.post("/chat", response_model=ChatResponse)
async def chat_completion(
    request: ChatRequest,
    user = Depends(get_current_user),
    llm = Depends(get_llm_provider),
    db = Depends(get_db),
    redis = Depends(get_redis)
):
    """
    AI Assistant endpoint with RBAC, rate limiting, token tracking, audit logs.
    """
    # RBAC check
    sub = await db.get_subscription_history(user['user_id'])
    if not sub or sub[0]['status'] != 'active':
        raise HTTPException(403, "Active subscription required for AI features")

    # Rate limit & token quota (Redis)
    user_key = f"ai_tokens:{user['user_id']}"
    daily_usage = await redis.get(user_key) or 0
    if int(daily_usage) > 10000:  # 10k token daily free tier
        raise HTTPException(429, "Daily AI token quota exceeded")

    try:
        # Call LLM
        response = await llm.chat_completion(
            messages=request.messages,
            model=request.model,
            max_tokens=request.max_tokens,
            temperature=request.temperature
        )
        
        # Track usage
        usage = {"tokens": request.max_tokens}  # Approximate
        new_usage = int(daily_usage) + request.max_tokens
        await redis.setex(user_key, 86400, new_usage)  # 24h TTL

        # Audit log
        await db.log_audit_event(
            action="ai_chat",
            person_id=user['user_id'],
            details={
                "model": request.model,
                "tokens_used": request.max_tokens,
                "messages_count": len(request.messages)
            }
        )

        logger.info(f"AI chat for user {user['user_id']}: {len(request.messages)} msgs, {request.max_tokens} tokens")
        return ChatResponse(response=response, usage=usage, status="success")

    except Exception as e:
        logger.error(f"AI chat error for {user['user_id']}: {e}")
        raise HTTPException(500, "AI service unavailable")

