from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.dependencies import get_db
from app.models.message import Message
from app.schemas.message import (
    MessageCreate,
    MessageListResponse,
    MessageResponse,
)


router = APIRouter(
    prefix="/api/messages",
    tags=["Messages"],
)


@router.post(
    "",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    message_data: MessageCreate,
    db: Session = Depends(get_db),
):
    message = Message(
        message_text=message_data.message_text,
    )

    db.add(message)
    db.commit()
    db.refresh(message)

    return message


@router.get(
    "",
    response_model=MessageListResponse,
)
def list_messages(
    search: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(Message)

    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.filter(
            Message.message_text.ilike(search_pattern)
        )

    total = query.count()

    messages = (
        query
        .order_by(Message.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return MessageListResponse(
        items=messages,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{message_id}",
    response_model=MessageResponse,
)
def get_message(
    message_id: int,
    db: Session = Depends(get_db),
):
    message = db.get(Message, message_id)

    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found.",
        )

    return message