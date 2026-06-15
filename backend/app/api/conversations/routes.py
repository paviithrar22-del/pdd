from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.base import get_db
from app.api.auth.routes import get_current_user
from app.models.user import User
from app.models.content import Conversation, Message
from app.models.moderation import ModerationResult

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("")
def list_conversations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    convs = db.query(Conversation).order_by(Conversation.risk_score.desc()).limit(50).all()
    return {"success": True, "message": "OK", "data": [
        {
            "id": c.id,
            "participant": c.participant,
            "risk_score": round(float(c.risk_score or 0), 1),
            "message_count": c.message_count,
            "flagged_count": c.flagged_count,
        } for c in convs
    ]}


@router.get("/{conv_id}")
def conversation_detail(conv_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        return {"success": False, "message": "Not found", "data": {}}
    msgs = db.query(Message).filter(Message.conversation_id == conv_id).order_by(Message.timestamp.desc()).limit(50).all()
    return {"success": True, "message": "OK", "data": {
        "conversation": {
            "id": conv.id,
            "participant": conv.participant,
            "risk_score": round(float(conv.risk_score or 0), 1),
            "message_count": conv.message_count,
            "flagged_count": conv.flagged_count,
        },
        "messages": [
            {"id": m.id, "sender": m.sender, "content": m.content, "timestamp": m.timestamp}
            for m in msgs
        ],
    }}


@router.get("/{conv_id}/intelligence")
def conversation_intelligence(conv_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Conversation Intelligence — analyzes entire DM thread for escalation,
    threat density, abuse frequency, and category breakdown.
    This is Domain 7: Conversation Intelligence.
    """
    from app.services.analysis_pipeline import (
        calculate_threat_density,
        get_conversation_escalation,
        calculate_abuse_frequency,
    )

    conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
    if not conv:
        return {"success": False, "message": "Not found", "data": {}}

    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conv_id)
        .order_by(Message.timestamp.asc())
        .all()
    )
    message_ids = [m.id for m in messages]

    moderation_results = []
    if message_ids:
        moderation_results = (
            db.query(ModerationResult)
            .filter(
                ModerationResult.content_type == "message",
                ModerationResult.content_id.in_(message_ids),
            )
            .order_by(ModerationResult.created_at.asc())
            .all()
        )

    category_counts: dict = {}
    for m in moderation_results:
        category_counts[m.category] = category_counts.get(m.category, 0) + 1

    return {"success": True, "message": "OK", "data": {
        "conversation_id": conv.id,
        "participant": conv.participant,
        "risk_score": round(float(conv.risk_score or 0), 1),
        "message_count": conv.message_count,
        "flagged_count": conv.flagged_count,
        "threat_density_percent": calculate_threat_density(conv.flagged_count or 0, conv.message_count or 0),
        "escalation": get_conversation_escalation(moderation_results),
        "abuse_frequency_per_day": calculate_abuse_frequency(messages, conv.flagged_count or 0),
        "category_breakdown": [{"category": c, "count": n} for c, n in category_counts.items()],
    }}
