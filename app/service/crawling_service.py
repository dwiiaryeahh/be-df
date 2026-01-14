from sqlalchemy.orm import Session
from app.db.models import Crawling

def upsert_crawling(db: Session, timestamp: str, rsrp: str, taType: str, ulCqi: str, ulRssi: str, imsi: str, ip: str, campaign_id: int = None) -> Crawling:
    # Cek apakah ada crawling dengan campaign_id dan imsi yang sama
    if campaign_id is not None:
        existing = db.query(Crawling).filter(
            Crawling.campaign_id == campaign_id,
            Crawling.imsi == imsi
        ).first()
    else:
        # Jika campaign_id None, cari yang campaign_id None dan imsi sama
        existing = db.query(Crawling).filter(
            Crawling.campaign_id == None,
            Crawling.imsi == imsi
        ).first()
    
    if existing:
        # UPDATE existing record
        existing.timestamp = timestamp
        existing.rsrp = rsrp
        existing.taType = taType
        existing.ulCqi = ulCqi
        existing.ulRssi = ulRssi
        existing.ip = ip
        row = existing
    else:
        # INSERT new record
        row = Crawling(
            timestamp=timestamp,
            rsrp=rsrp,
            taType=taType,
            ulCqi=ulCqi,
            ulRssi=ulRssi,
            imsi=imsi,
            ip=ip,
            campaign_id=campaign_id,
        )
        db.add(row)
    
    return row
