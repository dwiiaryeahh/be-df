from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
import time
import os
import xml.etree.ElementTree as ET
from app.db.database import get_db
from app.service.services import get_all_ips_db, get_send_command_instance, XML_TYPE_MAP, build_xml_path
from app.service.heartbeat_service import update_heartbeat
from app.config.utils import SetAppCfgExt, SetCellPara

router = APIRouter()

@router.get("/cell_para", tags=["Get XML"])
def get_cellpara(db: Session = Depends(get_db)):
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
                update_heartbeat(db, ip, file_path) if exists else None
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

@router.post("/set_app_cfg_ext", tags=["Set BBU"])
def set_appcfgext(
    provider: str = Query("telkomsel", description="Nama provider folder appcfg (mis: telkomsel, indosat, xl)"),
    db: Session = Depends(get_db)
):
    try:
        ip_list = get_all_ips_db(db)
        if not ip_list:
            raise HTTPException(status_code=404, detail="Tidak ada device di table heartbeat.")

        results = []
        for ip in ip_list:
            try:
                tree = ET.parse(f'app/mode/appcfg/{provider}/appcfgext_{ip}.xml')
                root = tree.getroot()
                msg = ET.tostring(root, encoding='utf-8').decode()
                appcfg = f'{SetAppCfgExt}  <?xml version="1.0" encoding="utf-8"?> ' + msg
                get_send_command_instance().command(ip, appcfg)
                results.append({"ip": ip, "status": "success", "provider": provider})
            except Exception as e:
                results.append({"ip": ip, "status": "error", "error": str(e), "provider": provider})

        return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": results}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": [{"error": str(e)}]}

@router.post("/set_cell_para", tags=["Set BBU"])
def set_appcfgext(
    provider: str = Query("telkomsel", description="Nama provider folder appcfg (mis: telkomsel, indosat, xl)"),
    db: Session = Depends(get_db)
):
    try:
        ip_list = get_all_ips_db(db)
        if not ip_list:
            raise HTTPException(status_code=404, detail="Tidak ada device di table heartbeat.")

        results = []
        for ip in ip_list:
            try:
                tree = ET.parse(f'app/mode/cellpara/{provider}/cellpara_{ip}.xml')
                root = tree.getroot()
                msg = ET.tostring(root, encoding='utf-8').decode()
                cellpara = f'{SetCellPara}  <?xml version="1.0" encoding="utf-8"?> ' + msg
                get_send_command_instance().command(ip, cellpara)
                results.append({"ip": ip, "status": "success", "provider": provider})
            except Exception as e:
                results.append({"ip": ip, "status": "error", "error": str(e), "provider": provider})

        return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": results}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": [{"error": str(e)}]}

@router.post("/set_blacklist", tags=["Set BBU"])
def set_blacklist(
    db: Session = Depends(get_db),
    imsi: str = Query(),
):
    try:
        ip_list = get_all_ips_db(db)
        if not ip_list:
            raise HTTPException(status_code=404, detail="Tidak ada device di table heartbeat.")
        
        cmd = f'SetBlacklist {imsi}'
        results = []
        for ip in ip_list:
            try:
                get_send_command_instance().command(ip, cmd)
                results.append({"ip": ip, "status": "success", })
            except Exception as e:
                results.append({"ip": ip, "status": "error", "error": str(e)})

        return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": results}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": [{"error": str(e)}]}

@router.post("/set_ul_para", tags=["Set BBU"])
def set_ul_para(
    db: Session = Depends(get_db),
):
    try:
        ip_list = get_all_ips_db(db)
        if not ip_list:
            raise HTTPException(status_code=404, detail="Tidak ada device di table heartbeat.")
        
        cmd = f'SetUlPcPara 40 30 1'
        results = []
        for ip in ip_list:
            try:
                get_send_command_instance().command(ip, cmd)
                results.append({"ip": ip, "status": "success", })
            except Exception as e:
                results.append({"ip": ip, "status": "error", "error": str(e)})

        return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": results}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": [{"error": str(e)}]}