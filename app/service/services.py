"""
Service layer - Business logic dan helper functions
"""
from typing import List, Dict
import os
import time
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import FreqOperator, Heartbeat, Crawling, Campaign, GPS, NmmCfg, Operator

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# -------------------------
# Helper: Ambil IP dari DB
# -------------------------
def get_all_ips_db(db: Session) -> List[str]:
    """Mengambil semua IP dari table heartbeat"""
    rows = db.query(Heartbeat.source_ip).all()
    return [r[0] for r in rows]

def get_ips_with_sniffer_enabled(db: Session) -> List[str]:
    """Ambil IP yang sniff_status = 1 (ada modul sniffer / nyala)."""
    rows = db.query(Heartbeat.source_ip).filter(
        Heartbeat.sniff_status == 1
    ).all()
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
    """Get current heartbeat snapshot dari DB untuk WebSocket - array format"""
    rows = db.query(Heartbeat).all()
    data = []
    
    for r in rows:
        data.append({
            "IP": r.source_ip,
            "STATE": r.state,
            "TEMP": r.temp,
            "MODE": r.mode,
            "CH": r.ch,
            "timestamp": r.timestamp,
        })
    
    return {
        "status": "success",
        "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
        "data": data,
    }


def crawling_snapshot(db: Session, campaign_id: int = None) -> dict:
    query = db.query(Crawling)
    
    if campaign_id is not None:
        query = query.filter(Crawling.campaign_id == campaign_id)
    
    rows = query.all()
    data = {
        r.imsi: {
            "timestamp": r.timestamp,
            "rsrp": r.rsrp,
            "taType": r.taType,
            "ulCqi": r.ulCqi,
            "ulRssi": r.ulRssi,
            "ip": r.ip,
            "campaign_id": r.campaign_id,
        }
        for r in rows
    }
    return {
        "status": "success",
        "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
        "campaign_id": campaign_id,
        "data": data,
    }


# ==========================================
# Heartbeat & Crawling Services
# ==========================================

def get_latest_campaign_id(db: Session) -> int:
    campaign = db.query(Campaign).order_by(Campaign.id.desc()).first()
    return campaign.id if campaign else None


def upsert_heartbeat(db: Session, source_ip: str, state: str, temp: str, mode: str, ch: str, timestamp: str) -> Heartbeat:
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

def insert_or_update_gps(latitude: str, longitude: str, timestamp: str):
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

def update_status_ip_sniffer(
    source_ip: str,
    update_type: str,
    value: int,
    db: Session
):
    heartbeat = db.query(Heartbeat).filter(
        Heartbeat.source_ip == source_ip
    ).first()

    if not heartbeat:
        print(f"[WARN] Heartbeat dengan IP {source_ip} tidak ditemukan")
        return False

    if update_type == "status":
        heartbeat.sniff_status = value

        if value == 0:
            heartbeat.sniff_scan = 0

    elif update_type == "scan":
        heartbeat.sniff_scan = value

        if value == 1:
            heartbeat.sniff_status = 1

    else:
        print(f"[ERROR] update_type tidak dikenal: {update_type}")
        return False

    heartbeat.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    db.commit()
    db.refresh(heartbeat)

    print(
        f"[OK] Update sniffer IP {source_ip} | "
        f"status={heartbeat.sniff_status}, scan={heartbeat.sniff_scan}"
    )
    return True

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def reset_nmmcfg(db: Session) -> int:
    """
    Hapus SEMUA data di tabel nmmcfg.
    Return: jumlah row yang kehapus.
    """
    try:
        deleted = db.query(NmmCfg).delete(synchronize_session=False)
        db.commit()
        print(f"[OK] nmmcfg reset. deleted={deleted}")
        return deleted
    except Exception as e:
        db.rollback()
        print("[ERROR] reset_nmmcfg:", e)
        raise


def insert_sniffer_nmmcfg(
    db: Session,
    ip: str = None,
    time: str = None,
    arfcn: int = None,
    operator: str = None,
    dl_freq: float = None,
    ul_freq: float = None,
    pci: str = None,
    rsrp: str = None,
    band: int = None,
):
    """
    Insert 1 row ke tabel nmmcfg.
    Field yang tidak ada -> None / default.
    """
    try:
        row = NmmCfg(
            ip=ip,
            time=now_str() if time is None else time,
            arfcn=arfcn,
            operator=operator,
            dl_freq=dl_freq,
            ul_freq=ul_freq,
            pci=pci,
            rsrp=rsrp,
            band=band,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        print("[OK] insert_sniffer_nmmcfg berhasil")
        return row
    except Exception as e:
        db.rollback()
        print("[ERROR] insert_sniffer_nmmcfg:", e)
        raise


def get_provider_data(db: Session, arfcn: int):
    """
    Ambil data provider berdasarkan arfcn dari tabel freq_operator + operator.brand.
    Output dibuat mirip kebutuhan insert nmmcfg:
      - brand -> operator
      - band, dl_freq, ul_freq, mode
    Kalau tidak ketemu -> semua None.
    """
    row = (
        db.query(
            FreqOperator.arfcn,
            Operator.brand.label("brand"),
            FreqOperator.band,
            FreqOperator.dl_freq,
            FreqOperator.ul_freq,
            FreqOperator.mode,
        )
        .join(Operator, Operator.id == FreqOperator.provider_id, isouter=True)
        .filter(FreqOperator.arfcn == arfcn)
        .first()
    )

    if not row:
        return {
            "arfcn": arfcn,
            "operator": None,
            "band": None,
            "dl_freq": None,
            "ul_freq": None,
            "mode": None,
        }

    return {
        "arfcn": row.arfcn,
        "operator": row.brand,   # mapping brand -> operator (kolom nmmcfg)
        "band": row.band,
        "dl_freq": row.dl_freq,
        "ul_freq": row.ul_freq,
        "mode": row.mode,
    }

# -------------------------
# Sniffing Data Functions
# -------------------------
def get_sniffing_progress(db: Session) -> Dict:
    heartbeats = db.query(Heartbeat).filter(Heartbeat.sniff_status == 1).all()
    
    if not heartbeats:
        return {
            'progress': 0,
            'status': 'idle',
            'last_update': None,
            'elapsed_minutes': 0,
            'total_devices': 0
        }
    
    total = len(heartbeats)
    completed = sum(1 for hb in heartbeats if hb.sniff_scan == -1)
    scanning = sum(1 for hb in heartbeats if hb.sniff_scan == 1)
    
    # Get latest timestamp
    latest_timestamp = None
    if heartbeats:
        try:
            timestamps = [float(hb.timestamp) for hb in heartbeats if hb.timestamp]
            if timestamps:
                latest_timestamp = max(timestamps)
        except (ValueError, TypeError):
            pass
    
    # Calculate elapsed time in minutes
    elapsed_minutes = 0
    if latest_timestamp:
        current_time = time.time()
        elapsed_minutes = (current_time - latest_timestamp) / 60
    
    # Determine status
    if scanning > 0 and elapsed_minutes < 5:
        status = 'scanning'
        progress = int((completed / total) * 100) if total > 0 else 0
    elif completed == total or elapsed_minutes >= 5:
        status = 'completed'
        progress = 100
    else:
        status = 'idle'
        progress = 0
    
    return {
        'progress': progress,
        'status': status,
        'last_update': latest_timestamp,
        'elapsed_minutes': round(elapsed_minutes, 2),
        'total_devices': total,
        'scanning_devices': scanning,
        'completed_devices': completed
    }

def get_heartbeat_sniff_status(db: Session) -> List[Dict]:
    heartbeats = db.query(Heartbeat).filter(Heartbeat.sniff_status == 1).all()
    result = []
    
    for hb in heartbeats:
        # Count sniff results (NmmCfg) untuk IP ini
        sniff_count = db.query(NmmCfg).filter(NmmCfg.ip == hb.source_ip).count()
        
        # Determine status label
        if hb.sniff_scan == -1:
            status_label = 'Sniff Stop'
        elif hb.sniff_scan == 1:
            status_label = 'Sniff Start'
        else:
            status_label = '-'
        
        result.append({
            'ip': hb.source_ip,
            'sniff_status': hb.sniff_status,
            'sniff_scan': hb.sniff_scan,
            'status_label': status_label,
            'sniff_count': sniff_count,
            'state': hb.state,
            'mode': hb.mode,
            'ch': hb.ch,
            'timestamp': hb.timestamp
        })
    
    return result


def get_nmmcfg_data(db: Session) -> List[Dict]:
    # Get IPs dari device yang sniff_status = 1
    active_devices = db.query(Heartbeat.source_ip).filter(Heartbeat.sniff_status == 1).all()
    active_ips = [ip[0] for ip in active_devices]
    
    # Get NmmCfg hanya dari active devices
    if not active_ips:
        return []
    
    nmmcfgs = db.query(NmmCfg).filter(NmmCfg.ip.in_(active_ips)).all()
    result = []
    
    for cfg in nmmcfgs:
        result.append({
            'id': cfg.id,
            'ip': cfg.ip,
            'time': cfg.time,
            'arfcn': cfg.arfcn,
            'operator': cfg.operator,
            'dl_freq': cfg.dl_freq,
            'ul_freq': cfg.ul_freq,
            'pci': cfg.pci,
            'rsrp': cfg.rsrp,
            'band': cfg.band
        })
    
    return result


def get_sniffing_data_snapshot(db: Session) -> Dict:
    return {
        'loading': get_sniffing_progress(db),
        'heartbeats': get_heartbeat_sniff_status(db),
        'nmmcfg_data': get_nmmcfg_data(db)
    }