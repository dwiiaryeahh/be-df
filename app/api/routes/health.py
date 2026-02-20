from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, time
from app.db.database import get_db
from app.service.log_service import list_logs

router = APIRouter()

@router.get("/logs", tags=["Logs"])
def logs(db: Session = Depends(get_db)):
    try:
        data = list_logs(db)
        return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "data": data}
    except Exception as e:
        return {"status": "error", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": [{"error": str(e)}]}

@router.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
        "database": db_status,
        "service": "IMSI CATCHER BACKEND"
    }
