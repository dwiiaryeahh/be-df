from typing import Dict
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.db.models import WbStatus

def get_wb_status(db: Session):
    try:
        wb_status = db.query(WbStatus).first()

        if not wb_status:
            return None

        return wb_status.status

    except Exception:
        return None

def update_wb_status(db: Session, new_status: bool) -> Dict:
    try:
        wb_status = db.query(WbStatus).first()
        
        if not wb_status:
            wb_status = WbStatus(
                status=new_status,
                updated_at=datetime.now(timezone.utc)
            )
            db.add(wb_status)
        else:
            wb_status.status = new_status
            wb_status.updated_at = datetime.now(timezone.utc)
        
        db.commit()
        db.refresh(wb_status)
        
        return {
            "status": "success",
            "message": f"WB Status updated to {new_status}",
            "data": {
                "id": wb_status.id,
                "status": wb_status.status,
                "updated_at": wb_status.updated_at.isoformat() if wb_status.updated_at else None
            }
        }
    
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": f"Failed to update WB Status: {str(e)}",
            "data": None
        }