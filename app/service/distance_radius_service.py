from typing import Optional, Dict
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.db.models import DistanceRadius
from app.db.schemas import RadiusRxTx
import xml.etree.ElementTree as ET

_DEFAULTS = dict(
    rx_lte=45,
    rx_wcdma=30,
    rx_gsm=65,
    tx_lte=5,
    tx_wcdma=5,
    tx_gsm=60,
)

_MODE_NODE_MAP = {
    "GSM":     ("rxGain",  "txPwr"),
    "FDD-LTE": ("rxGain",  "txPwrLevel"),
    "TDD-LTE": ("rxGain",  "txPwrLevel"),
    "WCDMA":   ("cpichPwr",   "power"),
    "GSM-WB":  ("rxGain",  "txPwr"),
}

_TECH_TO_MODE = {
    "lte":   "FDD-LTE",
    "wcdma": "WCDMA",
    "gsm":   "GSM",
}


def _ensure_row(db: Session) -> DistanceRadius:
    row = db.query(DistanceRadius).first()
    if not row:
        row = DistanceRadius(**_DEFAULTS)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def get_distance_radius(db: Session) -> Dict:
    row = _ensure_row(db)
    return _to_dict(row)


def update_distance_radius(
    db: Session,
    rx_lte: Optional[int] = None,
    rx_wcdma: Optional[int] = None,
    rx_gsm: Optional[int] = None,
    tx_lte: Optional[int] = None,
    tx_wcdma: Optional[int] = None,
    tx_gsm: Optional[int] = None,
) -> Dict:
    try:
        row = _ensure_row(db)

        if rx_lte   is not None: row.rx_lte   = rx_lte
        if rx_wcdma is not None: row.rx_wcdma = rx_wcdma
        if rx_gsm   is not None: row.rx_gsm   = rx_gsm
        if tx_lte   is not None: row.tx_lte   = tx_lte
        if tx_wcdma is not None: row.tx_wcdma = tx_wcdma
        if tx_gsm   is not None: row.tx_gsm   = tx_gsm

        row.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(row)
        
        return {"status": "success", "data": _to_dict(row)}

    except Exception as e:
        db.rollback()
        return {"status": "error", "message": str(e), "data": None}


def _to_dict(row: DistanceRadius) -> Dict:
    return {
        "id": row.id,
        "rx": {"lte": row.rx_lte, "wcdma": row.rx_wcdma, "gsm": row.rx_gsm},
        "tx": {"lte": row.tx_lte, "wcdma": row.tx_wcdma, "gsm": row.tx_gsm},
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }

def _apply_radius_to_xml(root: ET.Element, device_mode: str, radius: RadiusRxTx) -> None:
    tech_key = None
    for key, mode_str in _TECH_TO_MODE.items():
        if device_mode.upper() in (mode_str.upper(), key.upper()):
            tech_key = key
            break
    if tech_key is None:
        dm = device_mode.upper()
        if "LTE" in dm:
            tech_key = "lte"
        elif "WCDMA" in dm:
            tech_key = "wcdma"
        elif "GSM" in dm:
            tech_key = "gsm"

    if tech_key is None:
        return

    node_tags = _MODE_NODE_MAP.get(device_mode)
    if node_tags is None:
        for k, v in _MODE_NODE_MAP.items():
            if k.upper() == device_mode.upper():
                node_tags = v
                break
    if node_tags is None:
        return

    rx_tag, tx_tag = node_tags

    # RX
    if radius.rx is not None:
        rx_val = getattr(radius.rx, tech_key, None)
        if rx_val is not None:
            rx_node = root.find(f'.//{rx_tag}')
            if rx_node is not None:
                rx_node.text = str(rx_val)

    # TX
    if radius.tx is not None:
        tx_val = getattr(radius.tx, tech_key, None)
        if tx_val is not None:
            tx_node = root.find(f'.//{tx_tag}')
            if tx_node is not None:
                tx_node.text = str(tx_val)