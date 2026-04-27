"""
Pagination utilities and standard response models.
Ensures consistent pagination across all list endpoints.
"""
from typing import Generic, TypeVar, List, Optional, Dict, Any
from pydantic import BaseModel, Field
from typing_extensions import Annotated

T = TypeVar('T')

class PaginationParams:
    """Query parameters for pagination (shared across endpoints)"""
    def __init__(self, page: int = 1, limit: int = 50, sort_by: str = None, sort_order: str = "asc"):
        self.page = max(1, page)
        self.limit = min(100, max(1, limit))  # Cap at 100 per page
        self.sort_by = sort_by
        self.sort_order = sort_order.lower() if sort_order else "asc"
        self.offset = (self.page - 1) * self.limit
    
    @property
    def total(self) -> int:
        """Total pages (computed from total items)"""
        raise NotImplementedError
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "page": self.page,
            "limit": self.limit,
            "sort_by": self.sort_by,
            "sort_order": self.sort_order
        }


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard paginated response format used across all APIs.
    
    Example:
    {
        "success": true,
        "data": {
            "items": [...],
            "page": 1,
            "limit": 50,
            "total": 123,
            "total_pages": 3,
            "has_next": true,
            "has_prev": false
        },
        "error": null
    }
    """
    success: bool = True
    data: Dict[str, Any] = Field(..., description="Paginated data envelope")
    error: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {
                    "items": [],
                    "page": 1,
                    "limit": 50,
                    "total": 0,
                    "total_pages": 0,
                    "has_next": False,
                    "has_prev": False
                },
                "error": None
            }
        }


def create_paginated_response(
    items: List[Any],
    total: int,
    page: int,
    limit: int,
    additional_data: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Build a standardized paginated response dictionary.
    
    Args:
        items: List of items for current page
        total: Total number of items across all pages
        page: Current page number (1-indexed)
        limit: Items per page
        additional_data: Extra keys to include in data envelope
    
    Returns:
        Dict matching PaginatedResponse schema
    """
    total_pages = (total + limit - 1) // limit
    has_next = page < total_pages
    has_prev = page > 1
    
    data = {
        "items": items,
        "page": page,
        "limit": limit,
        "total": total,
        "total_pages": total_pages,
        "has_next": has_next,
        "has_prev": has_prev
    }
    
    if additional_data:
        data.update(additional_data)
    
    return {
        "success": True,
        "data": data,
        "error": None
    }


# Decorator for automatic pagination on endpoints
def paginated(endpoint_func):
    """
    Decorator to automatically wrap endpoint response in standard pagination format.
    
    Usage:
        @router.get("/persons")
        @paginated
        async def list_persons(params: PaginationParams = Depends()):
            # Return (items, total_count)
            return items, total_count
    """
    from functools import wraps
    
    @wraps(endpoint_func)
    async def wrapper(*args, **kwargs):
        result = await endpoint_func(*args, **kwargs) if asyncio.iscoroutinefunction(endpoint_func) else endpoint_func(*args, **kwargs)
        
        if isinstance(result, tuple) and len(result) == 2:
            items, total = result
            # Extract pagination params from kwargs or use defaults
            params = kwargs.get('params') or (args[0] if args else PaginationParams())
            page = getattr(params, 'page', 1)
            limit = getattr(params, 'limit', 50)
            return create_paginated_response(list(items), total, page, limit)
        return result
    
    return wrapper


# For non-async endpoints
def paginated_sync(endpoint_func):
    from functools import wraps
    
    @wraps(endpoint_func)
    def wrapper(*args, **kwargs):
        result = endpoint_func(*args, **kwargs)
        if isinstance(result, tuple) and len(result) == 2:
            items, total = result
            params = kwargs.get('params') or (args[0] if args else PaginationParams())
            page = getattr(params, 'page', 1)
            limit = getattr(params, 'limit', 50)
            return create_paginated_response(list(items), total, page, limit)
        return result
    
    return wrapper
