from app.celery_app import celery_app


@celery_app.task(name="health_check")
def health_check():
    return {"status": "ok", "service": "celery-worker"}
