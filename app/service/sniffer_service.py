from typing import List, Dict
import os
import time
from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import FreqOperator, Heartbeat, Crawling, Campaign, GPS, NmmCfg, Operator

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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

def reset_nmmcfg(db: Session) -> int:
    try:
        deleted = db.query(NmmCfg).delete(synchronize_session=False)
        db.commit()
        print(f"[OK] nmmcfg reset. deleted={deleted}")
        return deleted
    except Exception as e:
        db.rollback()
        print("[ERROR] reset_nmmcfg:", e)
        raise

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

    base_progress_per_device = 100.0 / total
    
    progress = completed * base_progress_per_device
    bonus_per_data = base_progress_per_device / 10
    
    for hb in heartbeats:
        if hb.sniff_scan == -1:
            continue
        
        sniff_count = db.query(NmmCfg).filter(NmmCfg.ip == hb.source_ip).count()
        bonus = min(sniff_count * bonus_per_data, base_progress_per_device * 0.9)
        progress += bonus
    
    if completed < total:
        progress = min(progress, 99)
    else:
        progress = 100
    
    progress = int(progress)
    
    latest_timestamp = None
    if heartbeats:
        try:
            timestamps = [float(hb.timestamp) for hb in heartbeats if hb.timestamp]
            if timestamps:
                latest_timestamp = max(timestamps)
        except (ValueError, TypeError):
            pass
    
    elapsed_minutes = 0
    if latest_timestamp:
        current_time = time.time()
        elapsed_minutes = (current_time - latest_timestamp) / 60
    
    if scanning > 0 and elapsed_minutes < 5:
        status = 'scanning'
    elif completed == total or elapsed_minutes >= 5:
        status = 'completed'
        for hb in heartbeats:
            if hb.sniff_scan != -1:
                hb.sniff_scan = -1
        db.commit()
    else:
        status = 'idle'
    
    return {
        'progress': progress,
        'status': status,
        'last_update': latest_timestamp,
        'elapsed_minutes': round(elapsed_minutes, 2),
        'total_devices': total,
        'scanning_devices': scanning,
        'completed_devices': completed
    }

def reset_nmmcfg(db: Session) -> int:
    try:
        deleted = db.query(NmmCfg).delete(synchronize_session=False)
        db.commit()
        print(f"[OK] nmmcfg reset. deleted={deleted}")
        return deleted
    except Exception as e:
        db.rollback()
        print("[ERROR] reset_nmmcfg:", e)
        raise

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