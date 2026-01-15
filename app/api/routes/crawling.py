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
from app.db.schemas import StartRequest, StartStatus, StopRequest, StopStatus, StartOneRequest, StopOneRequest
from app.service.services import get_all_ips_db, get_send_command_instance, get_ips_with_sniffer_enabled

router = APIRouter()


@router.post("/start_bbu", response_model=StartStatus, tags=["Crawling Imsi"])
def start_per_ip(req: StartOneRequest, db: Session = Depends(get_db)):
    try:
        ip = req.ip
        # Validasi IP format
        if not re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}", ip):
            raise HTTPException(status_code=400, detail="IP tidak valid.")

        # Cek IP ada di database
        ip_list = get_all_ips_db(db)
        if ip not in ip_list:
            raise HTTPException(status_code=404, detail=f"IP {ip} tidak ditemukan di table heartbeat.")

        try:
            get_send_command_instance().command(ip, StartCell)
            return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": [{"ip": ip, "status": "success"}]}
        except Exception as e:
            return {"status": "error", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": [{"ip": ip, "status": "error", "error": str(e)}]}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": [{"ip": "unknown", "status": "error", "error": str(e)}]}


@router.post("/start_all_bbu", response_model=StartStatus, tags=["Crawling Imsi"])
def start(db: Session = Depends(get_db)):
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


@router.post("/stop_bbu", response_model=StopStatus, tags=["Crawling Imsi"])
def stop_per_ip(req: StopOneRequest, db: Session = Depends(get_db)):
    try:
        ip = req.ip
        # Validasi IP format
        if not re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}", ip):
            raise HTTPException(status_code=400, detail="IP tidak valid.")

        # Cek IP ada di database
        ip_list = get_all_ips_db(db)
        if ip not in ip_list:
            raise HTTPException(status_code=404, detail=f"IP {ip} tidak ditemukan di table heartbeat.")

        try:
            get_send_command_instance().command(ip, StopCell)
            return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": [{"ip": ip, "status": "success"}]}
        except Exception as e:
            return {"status": "error", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": [{"ip": ip, "status": "error", "error": str(e)}]}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": [{"ip": "unknown", "status": "error", "error": str(e)}]}


@router.post("/stop_all_bbu", response_model=StopStatus, tags=["Crawling Imsi"])
def stop(db: Session = Depends(get_db)):
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

@router.post("/start_sniffing", response_model=StopStatus, tags=["Crawling Imsi"])
def start_sniffing(db: Session = Depends(get_db)):
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