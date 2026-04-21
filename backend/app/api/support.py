from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..schemas import SupportTicketCreate, SupportTicketResponse, SupportTicketUpdate
from ..db.db_client import get_db
from ..security import get_current_user
import uuid
from datetime import datetime

router = APIRouter()


@router.post("/support/tickets", response_model=SupportTicketResponse)
async def create_support_ticket(ticket: SupportTicketCreate, current_user=Depends(get_current_user)):
    """Create a new support ticket."""
    db = await get_db()
    ticket_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    await db.create_ticket(ticket_id, current_user["user_id"], ticket.subject, ticket.description, ticket.priority)

    return SupportTicketResponse(
        ticket_id=ticket_id,
        user_id=current_user["user_id"],
        subject=ticket.subject,
        description=ticket.description,
        priority=ticket.priority,
        status="open",
        created_at=created_at
    )


@router.get("/support/tickets", response_model=List[SupportTicketResponse])
async def get_support_tickets(current_user=Depends(get_current_user)):
    """Get all support tickets for the current user."""
    db = await get_db()
    tickets = await db.get_tickets(current_user["user_id"])

    return [
        SupportTicketResponse(
            ticket_id=t["ticket_id"],
            user_id=t["user_id"],
            subject=t["subject"],
            description=t["description"],
            priority=t["priority"],
            status=t["status"],
            created_at=t["created_at"].isoformat() if hasattr(t["created_at"], 'isoformat') else str(t["created_at"]),
            updated_at=t.get("updated_at")
        ) for t in tickets
    ]


@router.get("/support/tickets/{ticket_id}", response_model=SupportTicketResponse)
async def get_support_ticket(ticket_id: str, current_user=Depends(get_current_user)):
    """Get a specific support ticket."""
    db = await get_db()
    ticket = await db.get_ticket(ticket_id)

    if not ticket or ticket["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return SupportTicketResponse(
        ticket_id=ticket["ticket_id"],
        user_id=ticket["user_id"],
        subject=ticket["subject"],
        description=ticket["description"],
        priority=ticket["priority"],
        status=ticket["status"],
        created_at=ticket["created_at"].isoformat() if hasattr(ticket["created_at"], 'isoformat') else str(ticket["created_at"]),
        updated_at=ticket.get("updated_at")
    )


@router.put("/support/tickets/{ticket_id}", response_model=SupportTicketResponse)
async def update_support_ticket(ticket_id: str, update: SupportTicketUpdate, current_user=Depends(get_current_user)):
    """Update a support ticket."""
    db = await get_db()
    
    # Verify ownership
    ticket = await db.get_ticket(ticket_id)
    if not ticket or ticket["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Ticket not found")

    await db.update_ticket(ticket_id, update.description, update.priority)

    # Return updated ticket
    updated = await db.get_ticket(ticket_id)
    return SupportTicketResponse(
        ticket_id=updated["ticket_id"],
        user_id=updated["user_id"],
        subject=updated["subject"],
        description=updated["description"],
        priority=updated["priority"],
        status=updated["status"],
        created_at=updated["created_at"].isoformat() if hasattr(updated["created_at"], 'isoformat') else str(updated["created_at"]),
        updated_at=updated.get("updated_at")
    )


@router.delete("/support/tickets/{ticket_id}")
async def delete_support_ticket(ticket_id: str, current_user=Depends(get_current_user)):
    """Delete a support ticket."""
    db = await get_db()
    
    # Verify ownership
    ticket = await db.get_ticket(ticket_id)
    if not ticket or ticket["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Ticket not found")

    await db.delete_ticket(ticket_id)
    return {"message": "Ticket deleted successfully"}
