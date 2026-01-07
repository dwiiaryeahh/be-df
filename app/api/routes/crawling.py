"""
Crawling endpoints - Start/Stop BBU
Tags: Crawling Imsi
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import time
import re

from app.db.database import get_db
from app.config.utils import StartCell, StopCell
from app.db.schemas import StartRequest, StartStatus, StopRequest, StopStatus
from app.service.services import get_all_ips_db, get_send_command_instance, get_ips_with_sniffer_enabled

router = APIRouter()


# --- Endpoint POST dengan validasi SN ---
@router.post("/start_all_bbu", response_model=StartStatus, tags=["Crawling Imsi"])
def start(req: StartRequest, db: Session = Depends(get_db)):
    """
    Memulai StartCell via UDP berdasarkan IP dalam table heartbeat dan validasi SN.
    """
    if not re.fullmatch(r"[A-Za-z0-9]{8,20}", req.sn):
        raise HTTPException(status_code=400, detail="Serial number tidak valid. Harus 8–20 karakter alfanumerik.")

    try:
        ip_list = get_all_ips_db(db)
        if not ip_list:
            raise HTTPException(status_code=404, detail="Tidak ada device di table heartbeat.")

        results = []
        for ip in ip_list:
            try:
                get_send_command_instance().command(ip, StartCell)
                results.append({"ip": ip, "status": "success"})
            except Exception as e:
                results.append({"ip": ip, "status": "error", "error": str(e)})

        return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": results}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
                "details": [{"ip": "all", "status": "error", "error": str(e)}]}


@router.post("/stop_all_bbu", response_model=StopStatus, tags=["Crawling Imsi"])
def stop(req: StopRequest, db: Session = Depends(get_db)):
    """
    Mengirim perintah StopCell ke semua IP di table heartbeat dengan validasi SN.
    """
    if not re.fullmatch(r"[A-Za-z0-9]{8,20}", req.sn):
        raise HTTPException(status_code=400, detail="Serial number tidak valid. Harus 8–20 karakter alfanumerik.")

    try:
        ip_list = get_all_ips_db(db)
        if not ip_list:
            raise HTTPException(status_code=404, detail="Tidak ada device di table heartbeat.")

        results = []
        for ip in ip_list:
            try:
                get_send_command_instance().command(ip, StopCell)
                results.append({"ip": ip, "status": "success"})
            except Exception as e:
                results.append({"ip": ip, "status": "error", "error": str(e)})

        return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": results}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
                "details": [{"ip": "all", "status": "error", "error": str(e)}]}

@router.post("/start_sniffer", response_model=StopStatus, tags=["Crawling Imsi"])
def start_sniffer(req: StopRequest, db: Session = Depends(get_db)):
    """
    Mengirim perintah StartSniffer ke semua IP di table heartbeat dengan validasi SN.
    """
    if not re.fullmatch(r"[A-Za-z0-9]{8,20}", req.sn):
        raise HTTPException(status_code=400, detail="Serial number tidak valid. Harus 8–20 karakter alfanumerik.")

    try:
        ip_list = get_ips_with_sniffer_enabled(db)
        if not ip_list:
            raise HTTPException(status_code=404, detail="Tidak ada device di table heartbeat.")

        results = []
        for ip in ip_list:
            try:
                get_send_command_instance().command(ip, "StartSniffer")
                results.append({"ip": ip, "status": "success"})
            except Exception as e:
                results.append({"ip": ip, "status": "error", "error": str(e)})

        return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": results}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
                "details": [{"ip": "all", "status": "error", "error": str(e)}]}