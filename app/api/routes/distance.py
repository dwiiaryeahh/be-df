from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from pydantic import BaseModel
from sqlalchemy.orm import Session
import time
import os
import xml.etree.ElementTree as ET
from app.db.database import get_db
from app.db.models import Heartbeat
from app.db.schemas import RadiusRequest, RadiusRxTx, RadiusTech
from app.service.command_service import handle_get_cellpara
from app.service.log_service import list_logs
from app.service.utils_service import get_all_ips_db, get_send_command_instance, XML_TYPE_MAP, build_xml_path
from app.service.heartbeat_service import update_heartbeat
from app.config.utils import SetAppCfgExt, SetCellPara
from app.service.distance_radius_service import _apply_radius_to_xml, update_distance_radius, get_distance_radius, _DEFAULTS
from app.service.log_service import add_log

router = APIRouter()

@router.get("/get_distance", tags=["Distance"])
def get_distance(db: Session = Depends(get_db)):
    try:
        data = get_distance_radius(db)
        return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "data": data}
    except Exception as e:
        return {"status": "error", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": [{"error": str(e)}]}

@router.post("/set_distance", tags=["Distance"])
def set_distance(
    mode: str = Query("wb-24ch", description="Nama mode folder cellpara (mis: wb-24ch, telkomsel, indosat, xl)"),
    body: RadiusRequest = Body(default=RadiusRequest()),
    db: Session = Depends(get_db)
):
    try:
        ip_list = get_all_ips_db(db)
        if not ip_list:
            raise HTTPException(status_code=404, detail="Tidak ada device di table heartbeat.")

        results = []

        active_radius = body.radius
        if active_radius is None:
            active_radius = RadiusRxTx(
                rx=RadiusTech(
                    lte=str(_DEFAULTS["rx_lte"]),
                    wcdma=str(_DEFAULTS["rx_wcdma"]),
                    gsm=str(_DEFAULTS["rx_gsm"]),
                ),
                tx=RadiusTech(
                    lte=str(_DEFAULTS["tx_lte"]),
                    wcdma=str(_DEFAULTS["tx_wcdma"]),
                    gsm=str(_DEFAULTS["tx_gsm"]),
                ),
            )
            add_log(db, f"Distance Radius Reset to Default", "info", "User")

        for ip in ip_list:
            try:
                tree = ET.parse(f'app/mode/cellpara/{mode}/cellpara_{ip}.xml')
                root = tree.getroot()
                
                hb = db.query(Heartbeat).filter(Heartbeat.source_ip == ip).first()
                device_mode = hb.mode if hb else None
                if device_mode:
                    _apply_radius_to_xml(root, device_mode, active_radius)

                msg = ET.tostring(root, encoding='utf-8').decode()
                cellpara = f'{SetCellPara}  <?xml version="1.0" encoding="utf-8"?> ' + msg
                get_send_command_instance().command(ip, cellpara)
                results.append({"ip": ip, "status": "success", "mode": mode})
            except Exception as e:
                results.append({"ip": ip, "status": "error", "error": str(e), "mode": mode})
        
        # untuk update cellpara di /xml_file
        handle_get_cellpara(db, ip_list)

        # update radius di database jika ada request radius
        if active_radius is not None:
            rx = active_radius.rx
            tx = active_radius.tx
            update_distance_radius(
                db,
                rx_lte=int(rx.lte)     if rx and rx.lte   is not None else None,
                rx_wcdma=int(rx.wcdma) if rx and rx.wcdma is not None else None,
                rx_gsm=int(rx.gsm)     if rx and rx.gsm   is not None else None,
                tx_lte=int(tx.lte)     if tx and tx.lte   is not None else None,
                tx_wcdma=int(tx.wcdma) if tx and tx.wcdma is not None else None,
                tx_gsm=int(tx.gsm)     if tx and tx.gsm   is not None else None,
            )
            add_log(db, f"Distance Radius Updated", "info", "User")
        return {"status": "success", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": results}
    except HTTPException:
        raise
    except Exception as e:
        return {"status": "error", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": [{"error": str(e)}]}