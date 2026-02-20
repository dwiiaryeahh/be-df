from sqlalchemy.orm import Session
from app.db.models import Crawling
from app.service.gps_service import get_gps_data
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
import time
import re
from app.db.database import get_db
from app.db.schemas import CommandRequest, CommandResponse, CommandResult
from app.service.utils_service import get_all_ips_db
from app.service.mode_service import (
    execute_whitelist_mode,
    execute_blacklist_mode,
    execute_all_mode,
    execute_df_mode,
)

async def start_crawling(
    req: CommandRequest,
    db: Session = Depends(get_db)
):
    try:
        valid_modes = ['whitelist', 'blacklist', 'all', 'df']
        if req.mode.lower() not in valid_modes:
            raise HTTPException(
                status_code=400, 
                detail=f"Mode '{req.mode}' tidak valid. Mode yang valid: {', '.join(valid_modes)}"
            )
        
        if req.ip:
            if not re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}", req.ip):
                raise HTTPException(status_code=400, detail="Format IP tidak valid.")
            
            all_ips = get_all_ips_db(db)
            if req.ip not in all_ips:
                raise HTTPException(status_code=404, detail=f"IP {req.ip} tidak ditemukan.")
            
            ip_list = [req.ip]
        else:
            ip_list = get_all_ips_db(db)
            
            if not ip_list:
                raise HTTPException(status_code=404, detail="Tidak ada device aktif yang ditemukan.")
        
        if req.mode.lower() == 'df' and not req.provider:
            raise HTTPException(status_code=400, detail="Provider diperlukan untuk mode DF")
        
        mode_lower = req.mode.lower()
        if mode_lower == 'whitelist':
            return await execute_whitelist_mode(ip_list, req, db)
        elif mode_lower == 'blacklist':
            return await execute_blacklist_mode(ip_list, req, db)
        elif mode_lower == 'all':
            return await execute_all_mode(ip_list, req, db)
        elif mode_lower == 'df':
            return await execute_df_mode(ip_list, req, db)
            
    except HTTPException:
        raise
    except Exception as e:
        return CommandResponse(
            status="error",
            last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
            details=[CommandResult(ip="unknown", status="error", error=str(e))]
        )

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

