
from requests import Session
from app.db.models import Logs

def add_log(
    db: Session,
    description: str,
    type: str = "info",
    user: str = "system",
) -> Logs:
    log = Logs(description=description, type=type, user=user)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log

def list_logs(db: Session, limit: int = 100):
    return db.query(Logs).order_by(Logs.timestamp.desc()).limit(limit).all()
