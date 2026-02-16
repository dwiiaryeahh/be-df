"""
Unified Command Endpoint - Mode-based bundled commands
Tags: Command
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
import time
import re
from datetime import datetime
from app.db.database import get_db
from app.db.schemas import CommandRequest, CommandResponse, CommandResult
from app.service.utils_service import get_all_ips_db, get_send_command_instance
from app.utils.logger import setup_logger
from app.service.mode_service import (
    execute_whitelist_mode,
    execute_blacklist_mode,
    execute_all_mode,
    execute_df_mode,
)

router = APIRouter()
logger = setup_logger("command_api")

@router.post("/crawling/start", response_model=CommandResponse, tags=["Command"])
async def start_crawling(
    req: CommandRequest,
    db: Session = Depends(get_db)
):
    try:
        valid_modes = ['whitelist', 'blacklist', 'all', 'df']
        if req.mode.lower() not in valid_modes:
            raise HTTPException(
                status_code=400, 
                detail=f"Mode '{req.mode}' tidak valid. Mode yang valid: {', '.join(valid_modes)}"
            )
        
        if req.ip:
            if not re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}", req.ip):
                raise HTTPException(status_code=400, detail="Format IP tidak valid.")
            
            all_ips = get_all_ips_db(db)
            if req.ip not in all_ips:
                raise HTTPException(status_code=404, detail=f"IP {req.ip} tidak ditemukan.")
            
            ip_list = [req.ip]
        else:
            ip_list = get_all_ips_db(db)
            
            if not ip_list:
                raise HTTPException(status_code=404, detail="Tidak ada device aktif yang ditemukan.")
        
        if req.mode.lower() == 'df' and not req.provider:
            raise HTTPException(status_code=400, detail="Provider diperlukan untuk mode DF")
        
        mode_lower = req.mode.lower()
        if mode_lower == 'whitelist':
            return await execute_whitelist_mode(ip_list, req, db)
        elif mode_lower == 'blacklist':
            return await execute_blacklist_mode(ip_list, req, db)
        elif mode_lower == 'all':
            return await execute_all_mode(ip_list, req, db)
        elif mode_lower == 'df':
            return await execute_df_mode(ip_list, req, db)
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in unified_command: {e}")
        return CommandResponse(
            status="error",
            last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
            details=[CommandResult(ip="unknown", status="error", error=str(e))]
        )

@router.post("/cell/start", response_model=CommandResponse, tags=["Cell"])
async def start_cell_by_ip(
    ip: str,
    db: Session = Depends(get_db)
):
    """
    Start cell on specific IP address
    """
    try:
        # Validate IP format
        if not re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}", ip):
            raise HTTPException(status_code=400, detail="Format IP tidak valid.")
        
        # Check if IP exists in database
        all_ips = get_all_ips_db(db)
        if ip not in all_ips:
            raise HTTPException(status_code=404, detail=f"IP {ip} tidak ditemukan.")
        
        # Send StartCell command
        from app.config.utils import StartCell
        try:
            resp = get_send_command_instance().command(ip, StartCell)
            logger.info(f"[StartCell] IP: {ip}, Response: {resp}")
            
            return CommandResponse(
                status="success",
                last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
                details=[CommandResult(
                    ip=ip,
                    status="success",
                    message=f"StartCell command sent successfully. Response: {resp}"
                )]
            )
        except Exception as e:
            logger.error(f"[StartCell] Error on {ip}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to send StartCell command: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in start_cell_by_ip: {e}")
        return CommandResponse(
            status="error",
            last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
            details=[CommandResult(ip=ip, status="error", error=str(e))]
        )


@router.post("/cell/stop", response_model=CommandResponse, tags=["Cell"])
async def stop_cell_by_ip(
    ip: str,
    db: Session = Depends(get_db)
):
    """
    Stop cell on specific IP address
    """
    try:
        # Validate IP format
        if not re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}", ip):
            raise HTTPException(status_code=400, detail="Format IP tidak valid.")
        
        # Check if IP exists in database
        all_ips = get_all_ips_db(db)
        if ip not in all_ips:
            raise HTTPException(status_code=404, detail=f"IP {ip} tidak ditemukan.")
        
        # Send StopCell command
        from app.config.utils import StopCell
        try:
            resp = get_send_command_instance().command(ip, StopCell)
            logger.info(f"[StopCell] IP: {ip}, Response: {resp}")
            
            return CommandResponse(
                status="success",
                last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
                details=[CommandResult(
                    ip=ip,
                    status="success",
                    message=f"StopCell command sent successfully. Response: {resp}"
                )]
            )
        except Exception as e:
            logger.error(f"[StopCell] Error on {ip}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to send StopCell command: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in stop_cell_by_ip: {e}")
        return CommandResponse(
            status="error",
            last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
            details=[CommandResult(ip=ip, status="error", error=str(e))]
        )


@router.post("/sniffer/start", response_model=CommandResponse, tags=["Command"])
async def start_sniffer(db: Session = Depends(get_db)):
    try:
        ip_list = get_all_ips_db(db)
        
        if not ip_list:
            raise HTTPException(status_code=404, detail="Tidak ada device aktif yang ditemukan.")
        
        results = []
        for target_ip in ip_list:
            try:
                resp = get_send_command_instance().command(target_ip, "StartSniffer")                
                logger.debug(f"[StartSniffer] IP: {target_ip}, Response: {resp}")
                results.append(CommandResult(
                    ip=target_ip,
                    status="success",
                    message=f"Command sent. Response: {resp}"
                ))
            except Exception as e:
                logger.error(f"[StartSniffer] Error on {target_ip}: {e}")
                results.append(CommandResult(ip=target_ip, status="error", error=str(e)))
        
        return CommandResponse(
            status="success",
            last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
            details=results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in start_sniffer: {e}")
        return CommandResponse(
            status="error",
            last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
            details=[CommandResult(ip="unknown", status="error", error=str(e))]
        )


@router.post("/whitelist/get", response_model=CommandResponse, tags=["Command"])
async def get_whitelist(
    ip: str,
    db: Session = Depends(get_db)
):
    """
    Get Whitelist from specific IP address
    """
    try:
        # Validate IP format
        if not re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}", ip):
            raise HTTPException(status_code=400, detail="Format IP tidak valid.")
        
        # Check if IP exists in database
        all_ips = get_all_ips_db(db)
        if ip not in all_ips:
            raise HTTPException(status_code=404, detail=f"IP {ip} tidak ditemukan.")
        
        # Send GetWhiteList command
        from app.config.utils import GetWhiteList
        try:
            resp = get_send_command_instance().command(ip, GetWhiteList)
            logger.info(f"[GetWhiteList] IP: {ip}, Response: {resp}")
            
            return CommandResponse(
                status="success",
                last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
                details=[CommandResult(
                    ip=ip,
                    status="success",
                    message=f"GetWhiteList command sent successfully. Response: {resp}"
                )]
            )
        except Exception as e:
            logger.error(f"[GetWhiteList] Error on {ip}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to send GetWhiteList command: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_whitelist: {e}")
        return CommandResponse(
            status="error",
            last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
            details=[CommandResult(ip=ip, status="error", error=str(e))]
        )


@router.post("/blacklist/get", response_model=CommandResponse, tags=["Command"])
async def get_blacklist(
    ip: str,
    db: Session = Depends(get_db)
):
    """
    Get Blacklist from specific IP address
    """
    try:
        # Validate IP format
        if not re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}", ip):
            raise HTTPException(status_code=400, detail="Format IP tidak valid.")
        
        # Check if IP exists in database
        all_ips = get_all_ips_db(db)
        if ip not in all_ips:
            raise HTTPException(status_code=404, detail=f"IP {ip} tidak ditemukan.")
        
        # Send GetBlackList command
        from app.config.utils import GetBlackList
        try:
            resp = get_send_command_instance().command(ip, GetBlackList)
            logger.info(f"[GetBlackList] IP: {ip}, Response: {resp}")
            
            return CommandResponse(
                status="success",
                last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
                details=[CommandResult(
                    ip=ip,
                    status="success",
                    message=f"GetBlackList command sent successfully. Response: {resp}"
                )]
            )
        except Exception as e:
            logger.error(f"[GetBlackList] Error on {ip}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to send GetBlackList command: {str(e)}")
    except HTTPException:
        raise       
    except Exception as e:
        logger.error(f"Error in reboot_cell_by_ip: {e}")
        return CommandResponse(
            status="error",
            last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
            details=[CommandResult(ip=ip, status="error", error=str(e))]
        )


@router.post("/cell/reboot", response_model=CommandResponse, tags=["Cell"])
async def reboot_cell_by_ip(
    ip: str,
    db: Session = Depends(get_db)
):
    """
    Reboot cell on specific IP address (Command: Reboot 0)
    """
    try:
        # Validate IP format
        if not re.fullmatch(r"(\d{1,3}\.){3}\d{1,3}", ip):
            raise HTTPException(status_code=400, detail="Format IP tidak valid.")
        
        # Check if IP exists in database
        all_ips = get_all_ips_db(db)
        if ip not in all_ips:
            raise HTTPException(status_code=404, detail=f"IP {ip} tidak ditemukan.")
        
        # Send Reboot 0 command
        command_str = "Reboot 0"
        try:
            resp = get_send_command_instance().command(ip, command_str)
            logger.info(f"[RebootCell] IP: {ip}, Command: {command_str}, Response: {resp}")
            
            return CommandResponse(
                status="success",
                last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
                details=[CommandResult(
                    ip=ip,
                    status="success",
                    message=f"Reboot command sent successfully. Response: {resp}"
                )]
            )
        except Exception as e:
            logger.error(f"[RebootCell] Error on {ip}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to send Reboot command: {str(e)}")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in reboot_cell_by_ip: {e}")
        return CommandResponse(
            status="error",
            last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
            details=[CommandResult(ip=ip, status="error", error=str(e))]
        )