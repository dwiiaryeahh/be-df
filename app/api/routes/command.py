"""
Unified Command Endpoint - Topic-based routing untuk semua command
Tags: Command
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
import time
import re
import os
import xml.etree.ElementTree as ET

from app.db.database import get_db
from app.config.utils import StartCell, StopCell, SetAppCfgExt, SetCellPara
from app.db.schemas import CommandRequest, CommandResponse, CommandResult
from app.service.services import get_all_ips_db, get_send_command_instance, get_ips_with_sniffer_enabled, XML_TYPE_MAP, build_xml_path
from app.service.heartbeat_service import update_heartbeat

router = APIRouter()


@router.post("/command", response_model=CommandResponse, tags=["Command"])
def unified_command(
    topic: str = Query(..., description="Topic command yang akan dijalankan"),
    req: CommandRequest = CommandRequest(),
    db: Session = Depends(get_db)
):
    """
    Unified command endpoint dengan topic-based routing.
    
    Supported topics:
    - StartCell: Start BBU
    - StopCell: Stop BBU
    - StartSniffer: Start sniffer
    - GetCellPara: Get cell parameter
    - GetAppCfgExt: Get app config extended
    - GetBlackList: Get blacklist
    - SetAppCfgExt: Set app config extended
    - SetCellPara: Set cell parameter
    - SetBlackList: Set blacklist
    - SetWhiteList: Set whitelist
    - SetUlPara: Set UL PC parameter
    """
    try:
        if req.ip:
            if not re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}", req.ip):
                raise HTTPException(status_code=400, detail="IP tidak valid.")
            
            all_ips = get_all_ips_db(db)
            if req.ip not in all_ips:
                raise HTTPException(status_code=404, detail=f"IP {req.ip} tidak ditemukan di table heartbeat.")
            
            ip_list = [req.ip]
        elif req.all or topic in ['GetCellPara', 'GetAppCfgExt', 'GetBlackList', 'SetAppCfgExt', 'SetCellPara', 'SetBlackList', 'SetUlPara','SetWhiteList']:
            if topic == 'StartSniffer':
                ip_list = get_ips_with_sniffer_enabled(db)
            else:
                ip_list = get_all_ips_db(db)
            
            if not ip_list:
                raise HTTPException(status_code=404, detail="Tidak ada device di table heartbeat.")
        else:
            raise HTTPException(status_code=400, detail="Harus menyediakan 'ip' atau 'all': true")

        if topic == 'StartCell':
            return handle_start_cell(ip_list)
        elif topic == 'StopCell':
            return handle_stop_cell(ip_list)
        elif topic == 'StartSniffer':
            return handle_start_sniffer(ip_list)
        elif topic == 'GetCellPara':
            return handle_get_cellpara(ip_list, db)
        elif topic == 'GetAppCfgExt':
            return handle_get_appcfgext(ip_list, db)
        elif topic == 'GetBlackList':
            return handle_get_blacklist(ip_list, req.imsi)
        elif topic == 'SetAppCfgExt':
            return handle_set_xml(ip_list, 'appcfgext', req.provider)
        elif topic == 'SetCellPara':
            return handle_set_xml(ip_list, 'cellpara', req.provider)
        elif topic == 'SetBlackList':
            if not req.imsi:
                raise HTTPException(status_code=400, detail="IMSI diperlukan untuk topic SetBlackList")
            return handle_set_blacklist(ip_list, req.imsi)
        elif topic == 'SetWhiteList':
            if not req.imsi:
                raise HTTPException(status_code=400, detail="IMSI diperlukan untuk topic SetWhiteList")
            return handle_set_whitelist(ip_list, req.imsi)
        elif topic == 'SetUlPara':
            return handle_set_ulpara(ip_list)
        else:
            raise HTTPException(status_code=400, detail=f"Topic '{topic}' tidak dikenali. Topic yang valid: StartCell, StopCell, StartSniffer, GetCellPara, GetAppCfgExt, GetBlackList, SetAppCfgExt, SetCellPara, SetBlackList, SetUlPara")

    except HTTPException:
        raise
    except Exception as e:
        return CommandResponse(
            status="error",
            last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
            details=[CommandResult(ip="unknown", status="error", error=str(e))]
        )


# ==========================================
# Topic Handlers
# ==========================================

def handle_start_cell(ip_list: list) -> CommandResponse:
    """Handler untuk StartCell command"""
    results = []
    for ip in ip_list:
        try:
            get_send_command_instance().command(ip, StartCell)
            results.append(CommandResult(ip=ip, status="success"))
        except Exception as e:
            results.append(CommandResult(ip=ip, status="error", error=str(e)))
    
    return CommandResponse(
        status="success",
        last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
        details=results
    )


def handle_stop_cell(ip_list: list) -> CommandResponse:
    """Handler untuk StopCell command"""
    results = []
    for ip in ip_list:
        try:
            get_send_command_instance().command(ip, StopCell)
            results.append(CommandResult(ip=ip, status="success"))
        except Exception as e:
            results.append(CommandResult(ip=ip, status="error", error=str(e)))
    
    return CommandResponse(
        status="success",
        last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
        details=results
    )


def handle_start_sniffer(ip_list: list) -> CommandResponse:
    """Handler untuk StartSniffer command"""
    results = []
    for ip in ip_list:
        try:
            get_send_command_instance().command(ip, "StartSniffer")
            results.append(CommandResult(ip=ip, status="success"))
        except Exception as e:
            results.append(CommandResult(ip=ip, status="error", error=str(e)))
    
    return CommandResponse(
        status="success",
        last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
        details=results
    )


def handle_get_cellpara(ip_list: list, db: Session) -> CommandResponse:
    """Handler untuk GetCellPara command"""
    results = []
    for ip in ip_list:
        try:
            get_send_command_instance().command(ip, XML_TYPE_MAP["cell_para"]["get"])
            file_path = build_xml_path("cell_para", ip)
            exists = os.path.exists(file_path)
            update_heartbeat(db, ip, file_path) if exists else None
            msg = "File XML telah dibuat berdasarkan IP" if exists else "Perintah dikirim, menunggu file XML"
            results.append(CommandResult(
                ip=ip,
                status="success",
                file_exists=exists,
                file_path=file_path,
                message=msg
            ))
        except Exception as e:
            results.append(CommandResult(ip=ip, status="error", error=str(e)))
    
    return CommandResponse(
        status="success",
        last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
        details=results
    )


def handle_get_appcfgext(ip_list: list, db: Session) -> CommandResponse:
    """Handler untuk GetAppCfgExt command"""
    results = []
    for ip in ip_list:
        try:
            get_send_command_instance().command(ip, XML_TYPE_MAP["app_cfg_ext"]["get"])
            file_path = build_xml_path("app_cfg_ext", ip)
            exists = os.path.exists(file_path)
            msg = "File XML telah dibuat berdasarkan IP" if exists else "Perintah dikirim, menunggu file XML"
            results.append(CommandResult(
                ip=ip,
                status="success",
                file_exists=exists,
                file_path=file_path,
                message=msg
            ))
        except Exception as e:
            results.append(CommandResult(ip=ip, status="error", error=str(e)))
    
    return CommandResponse(
        status="success",
        last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
        details=results
    )


def handle_get_blacklist(ip_list: list, imsi: str = None) -> CommandResponse:
    """Handler untuk GetBlackList command"""
    cmd = 'GetBlackList'
    results = []
    for ip in ip_list:
        try:
            get_send_command_instance().command(ip, cmd)
            results.append(CommandResult(ip=ip, status="success"))
        except Exception as e:
            results.append(CommandResult(ip=ip, status="error", error=str(e)))
    
    return CommandResponse(
        status="success",
        last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
        details=results
    )

def handle_set_xml(ip_list: list, mode: str, provider: str = None) -> CommandResponse:
    results = []

    if mode == 'cellpara':
        command_name = SetCellPara
    elif mode == 'appcfgext':
        command_name = SetAppCfgExt
    else:
        raise ValueError(f"Unsupported mode: {mode}")

    for ip in ip_list:
        try:
            base_path = f'app/mode/{mode}/{provider}' if provider else f'app/mode/{mode}'
            tree = ET.parse(f'{base_path}/{mode}_{ip}.xml')
            root = tree.getroot()
            msg = ET.tostring(root, encoding='utf-8').decode()

            cmd = f'{command_name}  <?xml version="1.0" encoding="utf-8"?> {msg}'
            get_send_command_instance().command(ip, cmd)

            results.append(CommandResult(ip=ip, status="success", provider=provider))
        except Exception as e:
            results.append(CommandResult(ip=ip, status="error", error=str(e), provider=provider))

    return CommandResponse(
        status="success",
        last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
        details=results
    )



def handle_set_blacklist(ip_list: list, imsi: str) -> CommandResponse:
    """Handler untuk SetBlackList command"""
    cmd = f'SetBlackList {imsi}'
    results = []
    for ip in ip_list:
        try:
            get_send_command_instance().command(ip, cmd)
            results.append(CommandResult(ip=ip, status="success"))
        except Exception as e:
            results.append(CommandResult(ip=ip, status="error", error=str(e)))
    
    return CommandResponse(
        status="success",
        last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
        details=results
    )

def handle_set_whitelist(ip_list: list, imsi: str) -> CommandResponse:
    """Handler untuk SetWhiteList command"""
    cmd = f'SetWhiteList {imsi}'
    results = []
    for ip in ip_list:
        try:
            get_send_command_instance().command(ip, cmd)
            results.append(CommandResult(ip=ip, status="success"))
        except Exception as e:
            results.append(CommandResult(ip=ip, status="error", error=str(e)))
    
    return CommandResponse(
        status="success",
        last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
        details=results
    )


def handle_set_ulpara(ip_list: list) -> CommandResponse:
    """Handler untuk SetUlPara command"""
    cmd = 'SetUlPcPara 40 30 1'
    results = []
    for ip in ip_list:
        try:
            get_send_command_instance().command(ip, cmd)
            results.append(CommandResult(ip=ip, status="success"))
        except Exception as e:
            results.append(CommandResult(ip=ip, status="error", error=str(e)))
    
    return CommandResponse(
        status="success",
        last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
        details=results
    )
