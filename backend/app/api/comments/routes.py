from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List

from app.database.base import get_db
from app.models.content import Comment
from app.models.instagram import Post
from app.models.moderation import ModerationResult

router = APIRouter()

@router.get("/")
def get_comments(
    limit: int = Query(50, le=100),
    skip: int = Query(0),
    db: Session = Depends(get_db)
):
    """
    Returns recent comments with their moderation results.
    """
    # We want to join ModerationResult where content_type == 'comment' and content_id == Comment.id
    comments = (
        db.query(Comment, ModerationResult)
        .outerjoin(
            ModerationResult,
            (ModerationResult.content_id == Comment.id) & (ModerationResult.content_type == "comment")
        )
        .order_by(desc(Comment.id))
        .offset(skip)
        .limit(limit)
        .all()
    )

    results = []
    for comment, mod in comments:
        # Get associated post safely
        post = db.query(Post).filter(Post.id == comment.post_id).first()
        post_url = post.post_url if post else None

        results.append({
            "id": comment.id,
            "post_id": comment.post_id,
            "post_url": post_url,
            "author": comment.author,
            "content": comment.content,
            "moderation": {
                "toxicity_score": mod.toxicity_score if mod else None,
                "category": mod.category if mod else None,
                "severity": mod.severity if mod else None,
            } if mod else None
        })

    return {"comments": results}
