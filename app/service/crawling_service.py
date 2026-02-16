from sqlalchemy.orm import Session
from app.db.models import Crawling
from app.service.gps_service import get_gps_data

def upsert_crawling(
        db: Session, 
        timestamp: str, 
        rsrp: str, 
        taType: str, 
        ulCqi: str, 
        ulRssi: str, 
        imsi: str, 
        ip: str, 
        ch: str, 
        provider: str,
        imei: str = None,
        campaign_id: int = None
    ) -> Crawling:
    get_gps = get_gps_data(db)
    if campaign_id is not None:
        existing = db.query(Crawling).filter(
            Crawling.campaign_id == campaign_id,
            Crawling.imsi == imsi
        ).first()
    else:
        existing = db.query(Crawling).filter(
            Crawling.campaign_id == None,
            Crawling.imsi == imsi
        ).first()
    
    if existing:
        existing.timestamp = timestamp
        existing.rsrp = rsrp
        existing.taType = taType
        existing.ulCqi = ulCqi
        existing.ulRssi = ulRssi
        existing.ip = ip
        existing.ch = ch
        existing.provider = provider
        existing.lat = get_gps.latitude
        existing.long = get_gps.longitude
        existing.count = (existing.count or 0) + 1
        existing.imei = imei
        row = existing
    else:
        row = Crawling(
            timestamp=timestamp,
            rsrp=rsrp,
            taType=taType,
            ulCqi=ulCqi,
            ulRssi=ulRssi,
            imsi=imsi,
            ip=ip,
            ch=ch,
            provider=provider,
            campaign_id=campaign_id,
            lat=get_gps.latitude,
            long=get_gps.longitude,
            count=1,
            imei=imei
        )
        db.add(row)
    
    return row

