from sqlalchemy.orm import Session
from datetime import datetime
import time
import xml.etree.ElementTree as ET
import os
import asyncio

from app.config.utils import SetAppCfgExt, SetCellPara, StartCell, StopCell
from app.db.schemas import CommandResponse, CommandResult
from app.service.heartbeat_service import update_heartbeat
from app.service.utils_service import XML_TYPE_MAP, build_xml_path, get_send_command_instance
from app.utils.logger import setup_logger

logger = setup_logger("COMMAND_HANDLE")

async def handle_start_cell(ip_list: list, db: Session = None, mode: str = None, duration: str = None, imsi: str = None, is_resume: bool = False, current_elapsed: float = 0) -> CommandResponse:
    """Handler untuk StartCell command"""
    results = []
    for ip in ip_list:
        try:
            logger.debug(f"[StartCell] Sending StartCell to {ip}")
            get_send_command_instance().command(ip, StartCell)
            
            async def repeat_task(target_ip):
                logger.debug(f"[StartCell] Starting repeat_task for {target_ip} (2 times)")
                for i in range(2):
                    await asyncio.sleep(0.5)
                    try:
                        logger.debug(f"[StartCell] Repeat {i+1}/2 sending StartCell to {target_ip}")
                        get_send_command_instance().command(target_ip, StartCell)
                    except Exception as e:
                        logger.error(f"[StartCell] Background repeat error on {target_ip}: {e}")
            
            asyncio.create_task(repeat_task(ip))
            results.append(CommandResult(ip=ip, status="success"))
        except Exception as e:
            logger.error(f"[StartCell] Error sending to {ip}: {e}")
            results.append(CommandResult(ip=ip, status="error", error=str(e)))
    
    if db:
        from app.db.models import Campaign
        from app.service.timer_service import get_timer_ops_instance
        
        active_campaign = db.query(Campaign).filter(
            Campaign.status == 'started'
        ).order_by(Campaign.id.desc()).first()
        
        if active_campaign:
            if not is_resume:
                active_campaign.start_scan = datetime.now()
            
            if imsi:
                db_imsi = imsi.strip().replace(' ', ',')
                active_campaign.imsi = db_imsi
            
            db.commit()
            logger.info(f"[StartCell] Updated campaign {active_campaign.id}. Resume: {is_resume}")
            
            if duration:
                timer_ops = get_timer_ops_instance()
                timer_ops.start_timer(active_campaign.id, mode, duration, initial_elapsed=current_elapsed)
                logger.info(f"[StartCell] Started timer for campaign {active_campaign.id} (elapsed: {current_elapsed}s)")
    
    return CommandResponse(
        status="success",
        last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
        details=results
    )

async def handle_stop_cell(ip_list: list) -> CommandResponse:
    """Handler untuk StopCell command"""
    results = []
    for ip in ip_list:
        try:
            logger.debug(f"[StopCell] Sending StopCell to {ip}")
            get_send_command_instance().command(ip, StopCell)
            
            async def repeat_stop_task(target_ip):
                logger.debug(f"[StopCell] Starting repeat_stop_task for {target_ip} (2 times)")
                for i in range(2):
                    await asyncio.sleep(0.5)
                    try:
                        logger.debug(f"[StopCell] Repeat {i+1}/2 sending StopCell to {target_ip}")
                        get_send_command_instance().command(target_ip, StopCell)
                    except Exception as e:
                        logger.error(f"[StopCell] Background repeat error on {target_ip}: {e}")
            
            asyncio.create_task(repeat_stop_task(ip))
            results.append(CommandResult(ip=ip, status="success"))
        except Exception as e:
            logger.error(f"[StopCell] Error sending to {ip}: {e}")
            results.append(CommandResult(ip=ip, status="error", error=str(e)))
            
    return CommandResponse(
        status="success",
        last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
        details=results
    )

async def handle_set_ulpara(ip_list: list) -> CommandResponse:
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


async def handle_set_xml(ip_list: list, config: str, mode: str) -> CommandResponse:
    results = []
    if config == 'cellpara':
        command_name = SetCellPara
    elif config == 'appcfg':
        command_name = SetAppCfgExt
    else:
        raise ValueError(f"Unsupported config: {config}")

    for ip in ip_list:
        try:
            base_path = f'app/mode/{config}/{mode}'
            tree = ET.parse(f'{base_path}/{config}_{ip}.xml')
            root = tree.getroot()
            msg = ET.tostring(root, encoding='utf-8').decode()

            cmd = f'{command_name}  <?xml version="1.0" encoding="utf-8"?> {msg}'
            
            logger.debug(f"[SetXML] Sending {config} to {ip}")
            get_send_command_instance().command(ip, cmd)

            async def repeat_xml_task(target_ip, command_str):
                logger.debug(f"[SetXML] Starting repeat_xml_task for {target_ip} (2 times)")
                for i in range(2):
                    await asyncio.sleep(0.5)
                    try:
                        logger.debug(f"[SetXML] Repeat {i+1}/2 sending cmd to {target_ip}")
                        get_send_command_instance().command(target_ip, command_str)
                    except Exception as e:
                        logger.error(f"[SetXML] Background repeat error on {target_ip}: {e}")
            
            asyncio.create_task(repeat_xml_task(ip, cmd))

            results.append(CommandResult(ip=ip, status="success"))
        except Exception as e:
            logger.error(f"[SetXML] Error sending to {ip}: {e}")
            results.append(CommandResult(ip=ip, status="error", error=str(e)))

    return CommandResponse(
        status="success",
        last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
        details=results
    )

async def handle_set_blacklist(ip_list: list, imsi: str) -> CommandResponse:
    cmd = f'SetBlackList {imsi}' if imsi else 'SetBlackList '
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

async def handle_set_whitelist(ip_list: list, imsi: str) -> CommandResponse:
    cmd = f'SetWhiteList {imsi}' if imsi else 'SetWhiteList'
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

async def handle_get_cellpara(ip_list: list, db: Session) -> CommandResponse:
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
    
def handle_get_appcfgext(ip_list: list, db: Session):
    try:
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
    except Exception as e:
        results.append(CommandResult(ip=ip, status="error", error=str(e)))
    except Exception as e:
        return {"status": "error", "last_checked": time.strftime("%Y-%m-%d %H:%M:%S"), "details": [{"error": str(e)}]}

