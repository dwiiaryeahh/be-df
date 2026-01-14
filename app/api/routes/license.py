
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import time
from app.db.database import get_db
from app.db.models import License
router = APIRouter()

@router.get("/license", tags=["License"])
def get_licenses(db: Session = Depends(get_db)):
    licenses = db.query(License).all()
    
    data = [
        {
            "id": lic.id,
            "name": lic.name,
            "number": lic.number,
            "status": lic.status,
            "expires_at": lic.expires_at.isoformat() if lic.expires_at else None
        }
        for lic in licenses
    ]
    
    return {
        "status": "success",
        "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
        "data": data
    }

def update_license_status(db: Session, license_id: int, number: str):
    license_record = db.query(License).filter(License.id == license_id).first()
    if license_record:
        license_record.number = number
        license_record.status = "active"
        db.commit()
        return True
    return False