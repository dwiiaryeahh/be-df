from datetime import datetime
from sqlalchemy.orm import Session
from app.db.models import  Heartbeat
from app.service.services import parse_xml


def get_heartbeat_by_ip(
    db: Session,
    source_ip: str
) -> Heartbeat | None:
    return db.query(Heartbeat).filter(
        Heartbeat.source_ip == source_ip
    ).first()

def update_heartbeat(
    db: Session,
    source_ip: str,
    file_path: str
) -> Heartbeat | None:
    row = db.query(Heartbeat).filter(
        Heartbeat.source_ip == source_ip
    ).first()

    xml_parsing = parse_xml(file_path, row.mode)

    if not row:
        return None 

    row.mcc = xml_parsing.get("mcc", "")
    row.mnc = xml_parsing.get("mnc", "")
    row.band = xml_parsing.get("band", "")
    row.arfcn = xml_parsing.get("frequency", "")

    db.commit()
    db.refresh(row)

    return row

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

