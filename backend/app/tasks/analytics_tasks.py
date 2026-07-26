import logging
from datetime import date, datetime, timedelta, timezone

from celery import Celery

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

celery_app = Celery(
    "scout-analytics",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    broker_connection_retry_on_startup=False,
)
celery_app.conf.broker_connection_timeout = 2
celery_app.conf.result_backend_timeout = 2


@celery_app.task
def aggregate_daily_analytics(target_date_str: str | None = None):
    from app.db.session import SessionLocal
    from app.models import (
        ChatSession,
        DailyAnalytics,
        LLMUsage,
        KnowledgeSource,
        Message,
    )
    from sqlalchemy import func, cast, Date

    if target_date_str:
        target_date = date.fromisoformat(target_date_str)
    else:
        target_date = (datetime.now(timezone.utc) - timedelta(days=1)).date()

    db = SessionLocal()
    try:
        orgs = db.query(ChatSession.organization_id).distinct().all()

        for (org_id,) in orgs:
            day_start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
            day_end = datetime.combine(target_date, datetime.max.time()).replace(tzinfo=timezone.utc)

            chatbot_rows = (
                db.query(
                    Message.session_id,
                    ChatSession.chatbot_id,
                    ChatSession.organization_id,
                )
                .join(ChatSession)
                .filter(
                    ChatSession.organization_id == org_id,
                    Message.created_at >= day_start,
                    Message.created_at < day_end,
                )
                .distinct()
                .all()
            )

            chatbot_ids = set(r.chatbot_id for r in chatbot_rows)

            for chatbot_id in chatbot_ids:
                session_count = (
                    db.query(func.count(ChatSession.id))
                    .filter(
                        ChatSession.chatbot_id == chatbot_id,
                        ChatSession.started_at >= day_start,
                        ChatSession.started_at < day_end,
                    )
                    .scalar()
                    or 0
                )

                message_count = (
                    db.query(func.count(Message.id))
                    .join(ChatSession)
                    .filter(
                        ChatSession.chatbot_id == chatbot_id,
                        Message.created_at >= day_start,
                        Message.created_at < day_end,
                    )
                    .scalar()
                    or 0
                )

                token_row = (
                    db.query(
                        func.coalesce(func.sum(LLMUsage.prompt_tokens), 0),
                        func.coalesce(func.sum(LLMUsage.completion_tokens), 0),
                        func.coalesce(func.sum(LLMUsage.total_tokens), 0),
                    )
                    .filter(
                        LLMUsage.chatbot_id == chatbot_id,
                        LLMUsage.timestamp >= day_start,
                        LLMUsage.timestamp < day_end,
                    )
                    .first()
                )

                existing = (
                    db.query(DailyAnalytics)
                    .filter(
                        DailyAnalytics.date == target_date,
                        DailyAnalytics.organization_id == org_id,
                        DailyAnalytics.chatbot_id == chatbot_id,
                        DailyAnalytics.entity_type == "chatbot",
                    )
                    .first()
                )

                if existing:
                    existing.sessions_count = session_count
                    existing.messages_count = message_count
                    existing.prompt_tokens = token_row[0]
                    existing.completion_tokens = token_row[1]
                    existing.total_tokens = token_row[2]
                else:
                    da = DailyAnalytics(
                        date=target_date,
                        organization_id=org_id,
                        chatbot_id=chatbot_id,
                        entity_type="chatbot",
                        sessions_count=session_count,
                        messages_count=message_count,
                        prompt_tokens=token_row[0],
                        completion_tokens=token_row[1],
                        total_tokens=token_row[2],
                    )
                    db.add(da)

            db.commit()

        return {
            "status": "completed",
            "date": target_date.isoformat(),
            "organizations": len(orgs),
        }
    except Exception as e:
        logger.exception("Analytics aggregation failed")
        db.rollback()
        return {"status": "failed", "error": str(e)}
    finally:
        db.close()
