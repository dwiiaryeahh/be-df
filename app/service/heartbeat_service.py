import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import  Heartbeat
from app.service.utils_service import get_provider_by_mcc_mnc, get_provider_data, get_frequency_by_arfcn, parse_xml, provider_mapping
from app.ws.events import event_bus

def get_heartbeat_by_ip(
    db: Session,
    source_ip: str
) -> Heartbeat | None:
    return db.query(Heartbeat).filter(
        Heartbeat.source_ip == source_ip
    ).first()

# Dipakai untuk update ketika melakukan GetCellPara
def update_heartbeat(
    db: Session,
    source_ip: str,
    file_path: str
) -> Heartbeat | None:
    try:
        row = db.query(Heartbeat).filter(
            Heartbeat.source_ip == source_ip
        ).first()

        if not row:
            return None 

        xml_parsing = parse_xml(file_path, row.mode)
        
        arfcn_raw = xml_parsing.get("frequency", "")
        
        freq_data = get_frequency_by_arfcn(db, arfcn_raw)

        row.mcc = xml_parsing.get("mcc", "")
        row.mnc = xml_parsing.get("mnc", "")
        row.band = xml_parsing.get("band", "")
        row.arfcn = arfcn_raw
        row.dl_freq = freq_data.get("dl_freq", "")
        row.ul_freq = freq_data.get("ul_freq", "")

        db.commit()
        db.refresh(row)

        return row
    
    except Exception as e:
        print(f"[ERROR] Failed to update heartbeat for IP {source_ip}: {str(e)}")
        db.rollback()
        return None

# Dipakai ketika melakukan crawling IMSI (START BBU)
def upsert_heartbeat(db: Session, source_ip: str, state: str, temp: str, mode: str, ch: str, timestamp: str, band: str) -> Heartbeat:
    row = db.query(Heartbeat).filter(Heartbeat.source_ip == source_ip).first()
    if row:
        row.state = state
        row.temp = temp
        row.mode = mode
        row.ch = ch
        row.timestamp = timestamp
        row.band = band
    else:
        row = Heartbeat(
            source_ip=source_ip,
            state=state,
            temp=temp,
            mode=mode,
            ch=ch,
            timestamp=timestamp,
            band=band,
        )
        db.add(row)
    
    return row

# Dipakai ketika melakukan update status sniffer BBU
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


TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
def parse_timestamp(ts: str) -> datetime | None:
    try:
        return datetime.strptime(ts, TIME_FORMAT)
    except Exception:
        return None

async def heartbeat_checker(db: Session, check_count: int = 0):
    now = datetime.now()
    timeout_limit = now - timedelta(seconds=30)

    # Get ALL devices (including OFFLINE ones) to continuously broadcast status
    rows = db.query(Heartbeat).all()

    if not rows:
        return

    expired: list[Heartbeat] = []
    offline_devices: list[Heartbeat] = []

    for hb in rows:
        ts = parse_timestamp(hb.timestamp)
        if not ts:
            print(f"[WARN] Invalid timestamp for IP {hb.source_ip}: {hb.timestamp}")
            continue

        time_diff = (now - ts).total_seconds()
        
        if ts < timeout_limit and hb.state != "OFFLINE":
            print(f"[INFO] Device {hb.source_ip} timeout detected ({time_diff:.1f}s) - Setting to OFFLINE")
            hb.state = "OFFLINE"
            expired.append(hb)
        elif hb.state == "OFFLINE":
            offline_devices.append(hb)

    if expired:
        db.commit()

    for hb in expired:
        heartbeat_ws = {
            "type": "heartbeat",
            "ip": hb.source_ip,
            "state": "OFFLINE",
            "temp": hb.temp,
            "mode": hb.mode,
            "ch": hb.ch,
            "band": hb.band,
            "provider": get_provider_by_mcc_mnc(hb.mcc, hb.mnc),
            "mcc": hb.mcc,
            "mnc": hb.mnc,
            "arfcn": hb.arfcn,
            "timestamp": hb.timestamp,
            "ul" : hb.ul_freq,
            "dl" : hb.dl_freq,
        }

        await event_bus.send_heartbeat(heartbeat_ws)
        print(f"[OK] Sent OFFLINE status for {hb.source_ip} via WebSocket")

    if check_count % 10 == 0 and offline_devices:
        for hb in offline_devices:
            heartbeat_ws = {
                "type": "heartbeat",
                "ip": hb.source_ip,
                "state": "OFFLINE",
                "temp": hb.temp,
                "mode": hb.mode,
                "ch": hb.ch,
                "band": hb.band,
                "provider": get_provider_by_mcc_mnc(hb.mcc, hb.mnc),
                "mcc": hb.mcc,
                "mnc": hb.mnc,
                "arfcn": hb.arfcn,
                "timestamp": hb.timestamp,
                "ul" : hb.ul_freq,
                "dl" : hb.dl_freq,
            }

            await event_bus.send_heartbeat(heartbeat_ws)

async def heartbeat_watcher():
    print("[OK] Heartbeat watcher started (timeout: 30s, check interval: 1s)")
    check_count = 0
    while True:
        db = SessionLocal()
        try:
            await heartbeat_checker(db, check_count)
            check_count += 1
        except Exception as e:
            print("[HEARTBEAT WATCHER ERROR]", e)
        finally:
            db.close()

        await asyncio.sleep(1)