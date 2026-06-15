from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from pydantic import BaseModel
from typing import Optional
from app.database.base import get_db
from app.api.auth.routes import get_current_user
from app.models.user import User
from app.models.instagram import InstagramAccount
from app.models.content import Comment, Message, Conversation
from app.core.security import encrypt
from app.services.collector_service import start_monitoring, stop_monitoring, is_session_expired
from app.services.analysis_pipeline import analyze_content

router = APIRouter(prefix="/monitor", tags=["monitoring"])


class MonitorStartRequest(BaseModel):
    instagram_username: str
    instagram_password: str
    target_profile_url: Optional[str] = None


class IngestRequest(BaseModel):
    text: str
    author: str
    content_type: Optional[str] = "comment"  # "comment" or "message"


@router.post("/start")
def start(req: MonitorStartRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account = db.query(InstagramAccount).filter(
        InstagramAccount.user_id == user.id,
        InstagramAccount.account_username == req.instagram_username
    ).first()

    if not account:
        account = InstagramAccount(
            user_id=user.id,
            account_username=req.instagram_username,
            password_encrypted=encrypt(req.instagram_password),
        )
        db.add(account)
    else:
        account.password_encrypted = encrypt(req.instagram_password)

    account.monitoring_status = "running"
    account.session_started_at = datetime.utcnow()
    db.commit()
    db.refresh(account)

    start_monitoring(account, req.target_profile_url)
    return {"success": True, "message": "Monitoring started (session expires in 15 min)", "data": {"account_id": account.id}}


@router.post("/stop")
def stop(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    accounts = db.query(InstagramAccount).filter(
        InstagramAccount.user_id == user.id,
        InstagramAccount.monitoring_status == "running"
    ).all()
    for acc in accounts:
        stop_monitoring(acc.id)
        acc.monitoring_status = "stopped"
    db.commit()
    return {"success": True, "message": "Monitoring stopped", "data": {}}


@router.get("/status")
def status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    accounts = db.query(InstagramAccount).filter(InstagramAccount.user_id == user.id).all()
    result = []
    for acc in accounts:
        expired = is_session_expired(acc)
        if expired and acc.monitoring_status == "running":
            acc.monitoring_status = "stopped"
            db.commit()
        result.append({
            "account_id": acc.id,
            "username": acc.account_username,
            "status": acc.monitoring_status,
            "session_started_at": acc.session_started_at,
            "session_expired": expired,
        })
    return {"success": True, "message": "OK", "data": result}


@router.post("/ingest")
def ingest(req: IngestRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Manual Testing Mode (Mode 3) — Domain 17.
    Submits content directly into the analysis pipeline without Instagram.
    Allows the entire platform to be demonstrated and tested without scraping.

    Creates a real DB record so the result appears in violations, alerts, and
    offender/conversation views just like scraped content would.
    """
    if not req.text or not req.text.strip():
        return {"success": False, "message": "Text cannot be empty", "data": {}}

    content_type = req.content_type if req.content_type in ("comment", "message") else "comment"

    # Create a minimal stub record so analyze_content gets a valid content_id
    if content_type == "message":
        # Find or create a conversation for this author
        conv = db.query(Conversation).filter(Conversation.participant == req.author).first()
        if not conv:
            conv = Conversation(participant=req.author, message_count=0, flagged_count=0, risk_score=0.0)
            db.add(conv)
            db.commit()
            db.refresh(conv)

        record = Message(
            conversation_id=conv.id,
            sender=req.author,
            receiver=user.instagram_username or user.name,
            content=req.text,
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        content_id = record.id

        # Run full pipeline
        result = analyze_content(user.id, "message", content_id, req.text, req.author)

        # Update conversation counters
        conv.message_count = (conv.message_count or 0) + 1
        if result.get("toxicity_score", 0) > 0.3:
            conv.flagged_count = (conv.flagged_count or 0) + 1
        conv.risk_score = (conv.flagged_count / max(conv.message_count, 1)) * 100
        db.commit()

    else:
        # For comments: create a minimal stub without a real post (use post_id=0 sentinel not valid via FK)
        # Instead we link to a special "manual" post under a sentinel account
        account = db.query(InstagramAccount).filter(InstagramAccount.user_id == user.id).first()
        if not account:
            # Create a sentinel account for manual ingestion
            account = InstagramAccount(
                user_id=user.id,
                account_username=f"manual_{user.id}",
                monitoring_status="manual",
            )
            db.add(account)
            db.commit()
            db.refresh(account)

        from app.models.instagram import Post
        post = db.query(Post).filter(
            Post.account_id == account.id,
            Post.instagram_post_id == f"manual_{user.id}"
        ).first()
        if not post:
            post = Post(
                instagram_post_id=f"manual_{user.id}",
                account_id=account.id,
                post_url="manual://ingest",
            )
            db.add(post)
            db.commit()
            db.refresh(post)

        record = Comment(post_id=post.id, author=req.author, content=req.text)
        db.add(record)
        db.commit()
        db.refresh(record)
        content_id = record.id

        result = analyze_content(user.id, "comment", content_id, req.text, req.author)

    if not result:
        return {"success": True, "message": "Content is safe (no analysis triggered)", "data": {
            "toxicity_score": 0.0,
            "category": "safe",
            "severity": "Safe",
        }}

    return {"success": True, "message": "Content analyzed", "data": result}
