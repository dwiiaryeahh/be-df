"""
XML endpoints - Get/Set XML configuration
Tags: Get XML, Set XML
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import time
import os

from app.db.database import get_db
from app.db.schemas import SetXmlRequest
from app.service.services import get_all_ips_db, get_send_command_instance, XML_TYPE_MAP, build_xml_path

router = APIRouter()


@router.get("/cell_para", tags=["Get XML"])
def get_cellpara(db: Session = Depends(get_db)):
    """
    Kirim GetCellPara ke semua IP dari table heartbeat.
    """
    try:
        ip_list = get_all_ips_db(db)
        if not ip_list:
            raise HTTPException(status_code=404, detail="Tidak ada device di table heartbeat.")

        results = []
        for ip in ip_list:
            try:
                get_send_command_instance().command(ip, XML_TYPE_MAP["cell_para"]["get"])
                file_path = build_xml_path("cell_para", ip)
                exists = os.path.exists(file_path)
                msg = "File XML telah dibuat berdasarkan IP" if exists else "Perintah dikirim, menunggu file XML"
                results.append({"ip": ip, "status": "success", "file_exists": exists, "file_path": file_path, "message": msg})
            except Exception as e:
                results.append({"ip": ip, "status": "error", "error": str(e)})

        return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": results}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": [{"error": str(e)}]}


@router.get("/app_cfg_ext", tags=["Get XML"])
def get_appcfgext(db: Session = Depends(get_db)):
    """
    Kirim GetAppCfgExt ke semua IP dari table heartbeat.
    """
    try:
        ip_list = get_all_ips_db(db)
        if not ip_list:
            raise HTTPException(status_code=404, detail="Tidak ada device di table heartbeat.")

        results = []
        for ip in ip_list:
            try:
                get_send_command_instance().command(ip, XML_TYPE_MAP["app_cfg_ext"]["get"])
                file_path = build_xml_path("app_cfg_ext", ip)
                exists = os.path.exists(file_path)
                msg = "File XML telah dibuat berdasarkan IP" if exists else "Perintah dikirim, menunggu file XML"
                results.append({"ip": ip, "status": "success", "file_exists": exists, "file_path": file_path, "message": msg})
            except Exception as e:
                results.append({"ip": ip, "status": "error", "error": str(e)})

        return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": results}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": [{"error": str(e)}]}


@router.post("/set_xml", tags=["Set XML"])
def set_xml(req: SetXmlRequest, db: Session = Depends(get_db)):
    """Set XML configuration untuk device"""
    if req.type not in XML_TYPE_MAP:
        raise HTTPException(status_code=400, detail="type tidak dikenali")

    cmd = XML_TYPE_MAP[req.type]["set"]

    try:
        # Case 1: items (multi ip)
        if req.items:
            results = []
            for item in req.items:
                try:
                    ip = item.get("ip")
                    xml = item.get("xml")
                    file_path = build_xml_path(req.type, ip)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, "w") as f:
                        f.write(xml)
                    get_send_command_instance().command(ip, cmd)
                    exists = os.path.exists(file_path)
                    results.append({"ip": ip, "status": "success", "file_path": file_path, "file_exists": exists, "updated": True})
                except Exception as e:
                    results.append({"ip": item.get("ip"), "status": "error", "error": str(e)})

            return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": results}

        # Case 2: single ip
        if req.ip:
            file_path = build_xml_path(req.type, req.ip)
            if req.xml is not None:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, "w") as f:
                    f.write(req.xml)
            get_send_command_instance().command(req.ip, cmd)
            exists = os.path.exists(file_path)

            return {
                "status": "success",
                "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"),
                "details": [{"ip": req.ip, "file_path": file_path, "file_exists": exists, "updated": req.xml is not None}]
            }

        # Case 3: broadcast ke semua IP dari DB
        ip_list = get_all_ips_db(db)
        if not ip_list:
            raise HTTPException(status_code=404, detail="Tidak ada device di table heartbeat.")

        results = []
        for ip in ip_list:
            try:
                file_path = build_xml_path(req.type, ip)
                if req.xml is not None:
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, "w") as f:
                        f.write(req.xml)
                get_send_command_instance().command(ip, cmd)
                exists = os.path.exists(file_path)
                results.append({"ip": ip, "status": "success", "file_path": file_path, "file_exists": exists, "updated": req.xml is not None})
            except Exception as e:
                results.append({"ip": ip, "status": "error", "error": str(e)})

        return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": results}

    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": [{"error": str(e)}]}
