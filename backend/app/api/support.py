from fastapi import APIRouter, HTTPException, Depends
from typing import List
from ..schemas import SupportTicketCreate, SupportTicketResponse, SupportTicketUpdate
from ..db.db_client import get_db
from ..security import get_current_user
import uuid
from datetime import datetime

router = APIRouter()


@router.post("/support/tickets", response_model=SupportTicketResponse)
async def create_support_ticket(ticket: SupportTicketCreate, current_user=Depends(get_current_user), db=Depends(get_db)):
    """Create a new support ticket."""
    ticket_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    # Insert ticket into database
    query = """
    INSERT INTO support_tickets (ticket_id, user_id, subject, description, priority, status, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """
    await db.execute(query, (
        ticket_id,
        current_user["user_id"],
        ticket.subject,
        ticket.description,
        ticket.priority,
        "open",
        created_at
    ))

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
async def get_support_tickets(current_user=Depends(get_current_user), db=Depends(get_db)):
    """Get all support tickets for the current user."""
    query = "SELECT * FROM support_tickets WHERE user_id = ? ORDER BY created_at DESC"
    rows = await db.fetch_all(query, (current_user["user_id"],))

    return [
        SupportTicketResponse(
            ticket_id=row["ticket_id"],
            user_id=row["user_id"],
            subject=row["subject"],
            description=row["description"],
            priority=row["priority"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row.get("updated_at")
        ) for row in rows
    ]


@router.get("/support/tickets/{ticket_id}", response_model=SupportTicketResponse)
async def get_support_ticket(ticket_id: str, current_user=Depends(get_current_user), db=Depends(get_db)):
    """Get a specific support ticket."""
    query = "SELECT * FROM support_tickets WHERE ticket_id = ? AND user_id = ?"
    row = await db.fetch_one(query, (ticket_id, current_user["user_id"]))

    if not row:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return SupportTicketResponse(
        ticket_id=row["ticket_id"],
        user_id=row["user_id"],
        subject=row["subject"],
        description=row["description"],
        priority=row["priority"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row.get("updated_at")
    )


@router.put("/support/tickets/{ticket_id}", response_model=SupportTicketResponse)
async def update_support_ticket(ticket_id: str, update: SupportTicketUpdate, current_user=Depends(get_current_user), db=Depends(get_db)):
    """Update a support ticket."""
    # Check if ticket exists and belongs to user
    existing = await get_support_ticket(ticket_id, current_user, db)

    # Update ticket
    query = """
    UPDATE support_tickets SET description = ?, priority = ?, updated_at = ?
    WHERE ticket_id = ? AND user_id = ?
    """
    updated_at = datetime.utcnow().isoformat()
    await db.execute(query, (
        update.description or existing.description,
        update.priority or existing.priority,
        updated_at,
        ticket_id,
        current_user["user_id"]
    ))

    # Return updated ticket
    return await get_support_ticket(ticket_id, current_user, db)


@router.delete("/support/tickets/{ticket_id}")
async def delete_support_ticket(ticket_id: str, current_user=Depends(get_current_user), db=Depends(get_db)):
    """Delete a support ticket."""
    query = "DELETE FROM support_tickets WHERE ticket_id = ? AND user_id = ?"
    result = await db.execute(query, (ticket_id, current_user["user_id"]))

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Ticket not found")

    return {"message": "Ticket deleted successfully"}
