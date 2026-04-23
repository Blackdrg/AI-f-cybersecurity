from fastapi import APIRouter, Depends, Query
from typing import List, Optional
router = APIRouter()

@router.get("/logs")
async def get_logs(
    org_id: str,
    start_date: Optional[str] = Query(None),
    name: Optional[str] = Query(None)
):
    # Mock - production from DB
    logs = [
        {"timestamp": "2024-04-23 10:00", "person_name": "John Doe", "camera": "Entrance", "action": "Entry", "role": "staff"},
        {"timestamp": "2024-04-23 10:05", "person_name": "Jane Smith", "camera": "Exit", "action": "Exit", "role": "visitor"},
        {"timestamp": "2024-04-23 10:10", "person_name": "Unknown", "camera": "Entrance", "action": "Alert", "role": "unknown"},
    ]
    if start_date:
        logs = [l for l in logs if l['timestamp'] >= start_date]
    if name:
        logs = [l for l in logs if name.lower() in l['person_name'].lower()]
    return logs


