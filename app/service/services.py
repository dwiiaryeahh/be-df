"""
Service layer - Business logic dan helper functions
"""
from typing import List, Dict
import os
import time
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import Heartbeat, Crawling, Campaign

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# -------------------------
# Helper: Ambil IP dari DB
# -------------------------
def get_all_ips_db(db: Session) -> List[str]:
    """Mengambil semua IP dari table heartbeat"""
    rows = db.query(Heartbeat.source_ip).all()
    return [r[0] for r in rows]


def validate_token(token: str) -> bool:
    """Validasi token"""
    from app.config.utils import token_bbu
    return token == token_bbu


# -------------------------
# Lazy initialization untuk menghindari circular import
# -------------------------
_send_command_instance = None


def get_send_command_instance():
    """Get atau create send_command instance secara lazy"""
    global _send_command_instance
    if _send_command_instance is None:
        from app.controller import send_commend_modul
        _send_command_instance = send_commend_modul()
    return _send_command_instance


# -------------------------
# XML Configuration
# -------------------------
XML_TYPE_MAP = {
    "cell_para": {"get": "GetCellPara", "set": "SetCellPara", "folder": "cellpara"},
    "app_cfg_ext": {"get": "GetAppCfgExt", "set": "SetAppCfgExt", "folder": "appcfgext"},
    "nmm_para": {"get": "GetNmmCfg", "set": "SetNmmCfg", "folder": "nmmcfg"},
    "work_cfg": {"get": "GetBaseWorkCfg", "set": "SetBaseWorkCfg", "folder": "GetBaseWorkCfgRsp"},
    "app_cfg": {"get": "GetWeilanCfg", "set": "SetWeilanCfg", "folder": "GetWeilanCfgRsp"},
}


def build_xml_path(xml_type: str, ip: str) -> str:
    """Build path untuk XML file berdasarkan type dan IP"""
    folder = XML_TYPE_MAP[xml_type]["folder"]
    return os.path.join(BASE_DIR, "xml_file", folder, f"{folder}_{ip}.xml")


# -------------------------
# SUMMARY: dari DB (bukan JSON)
# -------------------------
def generate_summary_db(db: Session) -> Dict:
    """Generate summary dari database heartbeat dan crawling"""
    hb_rows = db.query(Heartbeat).all()
    # ambil set IP yang pernah muncul di crawling
    crawling_ips = {r[0] for r in db.query(Crawling.ip).distinct().all()}

    results = []
    found_count = 0
    not_found_count = 0

    for hb in hb_rows:
        ip = hb.source_ip
        if ip in crawling_ips:
            status = "FOUND"
            found_count += 1
        else:
            status = "NOT FOUND"
            not_found_count += 1

        results.append({
            "ip": ip,
            "TEMP": hb.temp,
            "MODE": hb.mode,
            "CH": hb.ch,
            "status": status
        })

    return {
        "results": results,
        "summary": {"FOUND": found_count, "NOT_FOUND": not_found_count}
    }


# -------------------------
# Heartbeat snapshot untuk WebSocket
# -------------------------
def heartbeat_snapshot(db: Session) -> dict:
    """Get current heartbeat snapshot dari DB untuk WebSocket"""
    rows = db.query(Heartbeat).all()
    data = {
        r.source_ip: {
            "STATE": r.state,
            "TEMP": r.temp,
            "MODE": r.mode,
            "CH": r.ch,
            "timestamp": r.timestamp,
        }
        for r in rows
    }
    return {
        "status": "success",
        "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
        "data": data,
    }


# ==========================================
# Heartbeat & Crawling Services
# ==========================================

def upsert_heartbeat(db: Session, source_ip: str, state: str, temp: str, mode: str, ch: str, timestamp: str) -> Heartbeat:
    """
    Insert atau update heartbeat data berdasarkan source_ip.
    
    Jika source_ip sudah ada → UPDATE, jika tidak → INSERT
    """
    row = db.query(Heartbeat).filter(Heartbeat.source_ip == source_ip).first()
    if row:
        row.state = state
        row.temp = temp
        row.mode = mode
        row.ch = ch
        row.timestamp = timestamp
    else:
        row = Heartbeat(
            source_ip=source_ip,
            state=state,
            temp=temp,
            mode=mode,
            ch=ch,
            timestamp=timestamp,
        )
        db.add(row)
    
    return row


def upsert_crawling(db: Session, timestamp: str, rsrp: str, taType: str, ulCqi: str, ulRssi: str, imsi: str, ip: str, campaign_id: int = None) -> Crawling:
    """
    Insert atau update crawling data.
    
    Logic:
    - Jika campaign_id dan imsi sama dengan record yang sudah ada, maka UPDATE
    - Selain itu, maka INSERT record baru
    """
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


# ==========================================
# Campaign Services - Untuk endpoint campaign
# ==========================================

def list_campaigns(db: Session) -> Dict:
    """List semua campaign dengan count crawling data"""
    campaigns = db.query(Campaign).all()
    
    result = []
    for campaign in campaigns:
        crawling_count = db.query(Crawling).filter(
            Crawling.campaign_id == campaign.id
        ).count()
        
        result.append({
            "id": campaign.id,
            "name": campaign.name,
            "imsi": campaign.imsi,
            "provider": campaign.provider,
            "status": campaign.status,
            "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
            "crawling_count": crawling_count
        })
    
    return {
        "status": "success",
        "message": "Campaign list retrieved",
        "data": result,
        "total": len(result)
    }


def create_campaign(db: Session, name: str, imsi: str, provider: str) -> Dict:
    """Create campaign baru (seperti start scan)"""
    campaign = Campaign(
        name=name,
        imsi=imsi,
        provider=provider,
        status="started"
    )
    
    try:
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        
        return {
            "status": "success",
            "message": "Campaign created successfully",
            "data": {
                "id": campaign.id,
                "name": campaign.name,
                "imsi": campaign.imsi,
                "provider": campaign.provider,
                "status": campaign.status,
                "created_at": campaign.created_at.isoformat() if campaign.created_at else None
            }
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": f"Failed to create campaign: {str(e)}",
            "data": None
        }


def get_campaign_detail(db: Session, campaign_id: int) -> Dict:
    """Get detail campaign dengan list crawling data"""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    
    if not campaign:
        return {
            "status": "error",
            "message": f"Campaign with id {campaign_id} not found",
            "data": None
        }
    
    crawlings = db.query(Crawling).filter(
        Crawling.campaign_id == campaign_id
    ).all()
    
    crawling_data = [
        {
            "id": c.id,
            "timestamp": c.timestamp,
            "rsrp": c.rsrp,
            "taType": c.taType,
            "ulCqi": c.ulCqi,
            "ulRssi": c.ulRssi,
            "imsi": c.imsi,
            "ip": c.ip
        }
        for c in crawlings
    ]
    
    return {
        "status": "success",
        "message": "Campaign detail retrieved",
        "data": {
            "id": campaign.id,
            "name": campaign.name,
            "imsi": campaign.imsi,
            "provider": campaign.provider,
            "status": campaign.status,
            "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
            "crawlings": crawling_data
        }
    }


def update_campaign_status(db: Session, campaign_id: int, new_status: str) -> Dict:
    """Update campaign status (misal: dari started -> stopped)"""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    
    if not campaign:
        return {
            "status": "error",
            "message": f"Campaign with id {campaign_id} not found",
            "data": None
        }
    
    try:
        campaign.status = new_status
        db.commit()
        db.refresh(campaign)
        
        return {
            "status": "success",
            "message": f"Campaign status updated to {new_status}",
            "data": {
                "id": campaign.id,
                "name": campaign.name,
                "imsi": campaign.imsi,
                "provider": campaign.provider,
                "status": campaign.status,
                "created_at": campaign.created_at.isoformat() if campaign.created_at else None
            }
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": f"Failed to update campaign: {str(e)}",
            "data": None
        }
