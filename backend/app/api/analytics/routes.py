from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, date, timezone
from app.database.base import get_db
from app.api.auth.routes import get_current_user
from app.models.user import User
from app.models.moderation import ModerationResult, Violation, Alert
from app.models.content import Comment, Message
from app.models.instagram import Post, InstagramAccount

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
def overview(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    account_ids = [a.id for a in db.query(InstagramAccount).filter(InstagramAccount.user_id == user.id).all()]
    post_ids = [p.id for p in db.query(Post).filter(Post.account_id.in_(account_ids)).all()] if account_ids else []

    total_posts = len(post_ids)
    total_comments = db.query(Comment).filter(Comment.post_id.in_(post_ids)).count() if post_ids else 0
    total_messages = db.query(Message).count()
    flagged = db.query(ModerationResult).filter(ModerationResult.toxicity_score > 0.3).count()
    critical_alerts = db.query(Alert).filter(Alert.user_id == user.id, Alert.severity == "Critical").count()
    unread_alerts = db.query(Alert).filter(Alert.user_id == user.id, Alert.status == "unread").count()

    # --- Today vs Yesterday delta (additive new keys) ---
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0).replace(tzinfo=None)
    yesterday_start = today_start - timedelta(days=1)

    flagged_today = (
        db.query(ModerationResult)
        .filter(
            ModerationResult.toxicity_score > 0.3,
            ModerationResult.created_at >= today_start,
        )
        .count()
    )
    flagged_yesterday = (
        db.query(ModerationResult)
        .filter(
            ModerationResult.toxicity_score > 0.3,
            ModerationResult.created_at >= yesterday_start,
            ModerationResult.created_at < today_start,
        )
        .count()
    )

    if flagged_yesterday > 0:
        percent_change = round(((flagged_today - flagged_yesterday) / flagged_yesterday) * 100, 1)
    elif flagged_today > 0:
        percent_change = 100.0
    else:
        percent_change = 0.0

    return {"success": True, "message": "OK", "data": {
        "total_posts": total_posts,
        "total_comments": total_comments,
        "total_messages": total_messages,
        "flagged_content": flagged,
        "critical_alerts": critical_alerts,
        "unread_alerts": unread_alerts,
        # New additive fields:
        "flagged_today": flagged_today,
        "flagged_yesterday": flagged_yesterday,
        "percent_change": percent_change,
    }}


@router.get("/trends")
def trends(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.analysis_pipeline import get_daily_violations_trend

    # Category distribution
    categories = db.query(
        ModerationResult.category, func.count(ModerationResult.id)
    ).group_by(ModerationResult.category).all()

    # Severity distribution
    severities = db.query(
        ModerationResult.severity, func.count(ModerationResult.id)
    ).group_by(ModerationResult.severity).all()

    # Top offenders — exclude bad identifiers (numeric IDs, 'Active', truncated usernames)
    BAD_PATTERN = ["%17%", "Active", "......"]
    offenders_q = db.query(
        Violation.user_identifier, func.count(Violation.id).label("count")
    ).group_by(Violation.user_identifier)
    for p in BAD_PATTERN:
        offenders_q = offenders_q.filter(~Violation.user_identifier.like(p))
    offenders = offenders_q.order_by(func.count(Violation.id).desc()).limit(10).all()

    # Daily violations trend (additive new key)
    daily_violations = get_daily_violations_trend(db, days=14)

    return {"success": True, "message": "OK", "data": {
        "category_distribution": [{"category": c, "count": n} for c, n in categories],
        "severity_distribution": [{"severity": s, "count": n} for s, n in severities],
        "top_offenders": [{"username": u, "violations": n} for u, n in offenders],
        "daily_violations": daily_violations,  # New additive field
    }}


@router.get("/offenders")
def offenders(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.analysis_pipeline import get_offender_level
    # Exclude bad identifiers (numeric IDs, 'Active', truncated usernames)
    BAD_PATTERN = ["%17%", "Active", "......"]
    q = db.query(
        Violation.user_identifier, func.count(Violation.id).label("count")
    ).group_by(Violation.user_identifier)
    for p in BAD_PATTERN:
        q = q.filter(~Violation.user_identifier.like(p))
    rows = q.order_by(func.count(Violation.id).desc()).limit(50).all()
    return {"success": True, "message": "OK", "data": [
        {"username": u, "violations": n, "risk_level": get_offender_level(n)} for u, n in rows
    ]}


@router.get("/offenders/{username}")
def offender_detail(username: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.analysis_pipeline import (
        get_offender_level,
        calculate_offender_score,
        get_risk_trend,
    )

    violations = (
        db.query(Violation)
        .filter(Violation.user_identifier == username)
        .order_by(Violation.created_at.desc())
        .all()
    )

    if not violations:
        return {"success": False, "message": "No violations found for this user", "data": {}}

    history = [
        {
            "id": v.id,
            "violation_type": v.violation_type,
            "severity": v.severity,
            "created_at": v.created_at,
        }
        for v in violations
    ]

    return {"success": True, "message": "OK", "data": {
        "username": username,
        "total_violations": len(violations),
        "offender_score": calculate_offender_score(violations),
        "offender_level": get_offender_level(len(violations)),
        "risk_trend": get_risk_trend(violations),
        "offense_history": history,
    }}