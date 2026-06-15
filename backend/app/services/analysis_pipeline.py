"""
Analysis Pipeline
Called after collector stores content.
Runs: moderation → severity → violation tracking → emergency trigger
"""
import logging
import asyncio
from datetime import datetime, timedelta, date, timezone
from collections import defaultdict
from sqlalchemy.orm import Session
from app.services.moderation_service import classify_text
from app.services.severity_service import calculate_severity, is_critical, is_threat_category
from app.services.emergency_service import trigger_emergency
from app.models.moderation import ModerationResult, Violation, Alert
from app.models.user import User

logger = logging.getLogger(__name__)

# WebSocket broadcaster (set by websocket module)
broadcast_fn = None

# Main asyncio event loop — set at FastAPI startup via set_main_loop().
# Required so the background scraper thread can safely schedule broadcasts
# onto the main loop via run_coroutine_threadsafe() instead of create_task()
# (which only works when you're already inside the loop's thread).
_main_loop = None


def set_main_loop(loop) -> None:
    """Called from main.py startup to capture the running FastAPI event loop."""
    global _main_loop
    _main_loop = loop
    logger.info("analysis_pipeline: main event loop captured")


def _broadcast(data: dict) -> None:
    """Thread-safe fire-and-forget broadcast. Works from any thread."""
    if not broadcast_fn or not _main_loop:
        return
    try:
        asyncio.run_coroutine_threadsafe(broadcast_fn(data), _main_loop)
    except Exception as exc:
        logger.debug(f"Broadcast skipped: {exc}")


def _get_prior_violations(db: Session, author: str) -> int:
    return db.query(Violation).filter(Violation.user_identifier == author).count()


def analyze_content(
    user_id: int,
    content_type: str,  # "comment" or "message"
    content_id: int,
    text: str,
    author: str,
) -> dict:
    if not text or not text.strip():
        return {}

    from app.database.base import SessionLocal
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return {}

        # 1. Classify
        mod = classify_text(text)
        toxicity_score = mod["toxicity_score"]
        category = mod["category"]
        confidence = mod["confidence"]

        # 2. Severity
        is_threat = is_threat_category(category)
        prior_violations = _get_prior_violations(db, author)
        sev = calculate_severity(toxicity_score, is_threat, prior_violations)
        severity_level = sev["severity_level"]
        severity_score = sev["severity_score"]

        # 3. Store moderation result
        result = ModerationResult(
            content_type=content_type,
            content_id=content_id,
            toxicity_score=toxicity_score,
            category=category,
            severity=severity_level,
            confidence=confidence,
        )
        db.add(result)

        # 4. Track violations
        if toxicity_score > 0.3:
            violation = Violation(
                user_identifier=author,
                violation_type=category,
                severity=severity_level,
            )
            db.add(violation)

        # 5. Create alert
        if toxicity_score > 0.3:
            alert = Alert(
                user_id=user.id,
                alert_type=category,
                severity=severity_level,
                content_preview=text[:200],
                status="unread",
            )
            db.add(alert)

        db.commit()

        # 6. Broadcast via WebSocket (thread-safe)
        if toxicity_score > 0.3:
            _broadcast({
                "event": f"new_{content_type}",
                "severity": severity_level,
                "category": category,
                "author": author,
            })

        # 7. Emergency
        if is_critical(severity_level):
            trigger_emergency(
                db=db,
                user=user,
                content_preview=text,
                severity_score=severity_score,
                severity_level=severity_level,
                incident_type=category,
                report_data={
                    "content_type": content_type,
                    "content_id": content_id,
                    "author": author,
                    "toxicity_score": toxicity_score,
                },
            )
            if is_critical(severity_level):
                _broadcast({"event": "emergency_triggered", "severity": severity_level})

        return {
            "toxicity_score": toxicity_score,
            "category": category,
            "severity": severity_level,
            "severity_score": severity_score,
        }
    finally:
        db.close()


def get_offender_level(violation_count: int) -> str:
    if violation_count == 0:
        return "Clean"
    elif violation_count <= 2:
        return "Low"
    elif violation_count <= 5:
        return "Medium"
    elif violation_count <= 10:
        return "High"
    return "Critical"

# Severity weighting used for offender score calculation
_SEVERITY_WEIGHTS = {"Safe": 0, "Moderate": 1, "High": 2, "Critical": 3}


def calculate_offender_score(violations: list) -> float:
    """
    Weighted 0-100 score based on severity of an offender's violation history.
    Higher severity violations contribute more than repeated low-severity ones.
    """
    if not violations:
        return 0.0
    total_weight = sum(_SEVERITY_WEIGHTS.get(v.severity, 0) for v in violations)
    score = min(total_weight * 5, 100)
    return float(score)


def get_risk_trend(violations: list) -> str:
    """
    Compares violation frequency in the last 7 days vs. the prior period
    to flag whether an offender's behavior is escalating, easing, or stable.
    """
    if len(violations) < 2:
        return "stable"

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=7)
    recent = sum(1 for v in violations if v.created_at and v.created_at >= cutoff)
    older = len(violations) - recent

    if recent > older:
        return "increasing"
    elif recent < older:
        return "decreasing"
    return "stable"


def get_daily_violations_trend(db: Session, days: int = 14) -> list:
    """
    Returns a day-by-day violation count for the last `days` days.
    Zero-fills days with no violations so the frontend always has a
    contiguous series: [{"date": "2026-06-01", "count": 5}, ...]
    """
    from app.models.moderation import Violation
    from sqlalchemy import func, cast
    import sqlalchemy.types as types

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)

    rows = (
        db.query(
            func.date(Violation.created_at).label("day"),
            func.count(Violation.id).label("count"),
        )
        .filter(Violation.created_at >= cutoff)
        .group_by(func.date(Violation.created_at))
        .all()
    )

    # Build a dict keyed by date string
    counts: dict = defaultdict(int)
    for row in rows:
        # func.date() returns a string in SQLite, date object in Postgres
        day_str = str(row.day)[:10]  # normalise to YYYY-MM-DD
        counts[day_str] = row.count

    # Generate a zero-filled contiguous series
    result = []
    for i in range(days - 1, -1, -1):
        day = (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=i)).date()
        day_str = day.isoformat()
        result.append({"date": day_str, "count": counts.get(day_str, 0)})

    return result


def calculate_threat_density(flagged_count: int, message_count: int) -> float:
    """
    Calculates the ratio of flagged messages to total messages as a percentage.
    """
    if message_count <= 0:
        return 0.0
    return round((flagged_count / message_count) * 100.0, 1)


def get_conversation_escalation(moderation_results: list) -> str:
    """
    Analyzes moderation results for escalation trend (escalating, de-escalating, stable, insufficient_data).
    """
    if len(moderation_results) < 3:
        return "insufficient_data"

    mid = len(moderation_results) // 2
    first_half = moderation_results[:mid]
    second_half = moderation_results[mid:]

    avg_first = sum(m.toxicity_score or 0.0 for m in first_half) / len(first_half)
    avg_second = sum(m.toxicity_score or 0.0 for m in second_half) / len(second_half)

    diff = avg_second - avg_first
    if diff > 0.15:
        return "escalating"
    elif diff < -0.15:
        return "de-escalating"
    else:
        return "stable"


def calculate_abuse_frequency(messages: list, flagged_count: int) -> float:
    """
    Calculates average abuse incidents per day, capping the duration to a minimum of 1 day.
    """
    if flagged_count <= 0 or not messages:
        return 0.0

    timestamps = [m.timestamp for m in messages if m.timestamp]
    if len(timestamps) < 2:
        return float(flagged_count)

    min_ts = min(timestamps)
    max_ts = max(timestamps)

    delta = max_ts - min_ts
    days = delta.total_seconds() / 86400.0

    return round(flagged_count / max(days, 1.0), 1)