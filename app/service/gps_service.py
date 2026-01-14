from app.db.models import GPS
from sqlalchemy.orm import Session

def get_gps_data(db:Session) -> GPS | None:
    return db.query(GPS).first()

def upsert_gps(latitude: str, longitude: str, timestamp: str):
    """Insert atau update data GPS di database"""
    from app.db.database import SessionLocal
    db = SessionLocal()
    try:
        gps_entry = db.query(GPS).first()
        if gps_entry:
            gps_entry.latitude = latitude
            gps_entry.longitude = longitude
            gps_entry.timestamp = timestamp
        else:
            gps_entry = GPS(
                latitude=latitude,
                longitude=longitude,
                timestamp=timestamp
            )
            db.add(gps_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error inserting/updating GPS data: {e}")
    finally:
        db.close()