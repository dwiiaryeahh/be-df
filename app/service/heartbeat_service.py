import asyncio
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import  Heartbeat
from app.service.services import get_provider_data, parse_xml, provider_mapping
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
    row = db.query(Heartbeat).filter(
        Heartbeat.source_ip == source_ip
    ).first()

    xml_parsing = parse_xml(file_path, row.mode)
    freq_provider = get_provider_data(db, xml_parsing.get("frequency"))

    if not row:
        return None 

    row.mcc = xml_parsing.get("mcc", "")
    row.mnc = xml_parsing.get("mnc", "")
    row.band = xml_parsing.get("band", "")
    row.arfcn = xml_parsing.get("frequency", "")
    row.dl_freq = freq_provider.get("dl_freq", "")
    row.ul_freq = freq_provider.get("ul_freq", "")

    db.commit()
    db.refresh(row)

    return row

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

async def heartbeat_checker(db: Session):
    now = datetime.now()
    timeout_limit = now - timedelta(seconds=30)

    rows = db.query(Heartbeat).filter(
        Heartbeat.state != "OFFLINE"
    ).all()

    if not rows:
        return

    expired: list[Heartbeat] = []

    for hb in rows:
        ts = parse_timestamp(hb.timestamp)
        if not ts:
            print(f"[WARN] Invalid timestamp for IP {hb.source_ip}: {hb.timestamp}")
            continue

        time_diff = (now - ts).total_seconds()
        
        if ts < timeout_limit:
            print(f"[INFO] Device {hb.source_ip} timeout detected ({time_diff:.1f}s) - Setting to OFFLINE")
            hb.state = "OFFLINE"
            expired.append(hb)

    if not expired:
        return

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
            "provider": provider_mapping(
                (hb.mcc or "") + (hb.mnc or "")
            ),
            "mcc": hb.mcc,
            "mnc": hb.mnc,
            "arfcn": hb.arfcn,
            "timestamp": hb.timestamp,  # ✅ GUNAKAN TIMESTAMP ASLI, BUKAN NOW
        }

        await event_bus.send_heartbeat(heartbeat_ws)
        print(f"[OK] Sent OFFLINE status for {hb.source_ip} via WebSocket")

async def heartbeat_watcher():
    print("[OK] Heartbeat watcher started (timeout: 5s, check interval: 1s)")
    while True:
        db = SessionLocal()
        try:
            await heartbeat_checker(db)
        except Exception as e:
            print("[HEARTBEAT WATCHER ERROR]", e)
        finally:
            db.close()

        await asyncio.sleep(1)