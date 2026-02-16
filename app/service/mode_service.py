import asyncio
import time
from sqlalchemy.orm import Session
from app.db.schemas import CommandResponse, CommandRequest
from app.service.utils_service import get_exception_ips
from app.service.command_service import (
    handle_set_ulpara,
    handle_set_xml,
    handle_set_blacklist,
    handle_set_whitelist,
    handle_get_cellpara,
    handle_start_cell
)
from app.utils.logger import setup_logger

logger = setup_logger("EXEC_MODE")

async def clear_whitelist_blacklist(ip_list: list) -> CommandResponse:
    all_results = []
    
    logger.info("[Clear] SetBlackList (empty)")
    result = await handle_set_blacklist(ip_list, "")
    all_results.extend(result.details)
        
    logger.info("[Clear] SetWhiteList (empty)")
    result = await handle_set_whitelist(ip_list, "")
    all_results.extend(result.details)
    
    return CommandResponse(
        status="success",
        last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
        details=all_results
    )

async def execute_whitelist_mode(ip_list: list, req: CommandRequest, db: Session) -> CommandResponse:
    logger.info(f"[Whitelist Mode] Starting bundle execution for {len(ip_list)} IPs")
    
    channels = get_exception_ips(db)
    exception_ips = channels['exception_ips']
    other_ips = channels['other_ips']
    
    exception_ips = [ip for ip in exception_ips if ip in ip_list]
    other_ips = [ip for ip in other_ips if ip in ip_list]
    
    all_results = []
    
    logger.info("[1/5] SetUlPara")
    result = await handle_set_ulpara(ip_list)
    all_results.extend(result.details)
    await asyncio.sleep(0.5)
    
    logger.info("[2/5] SetAppCfgExt (whitelist)")
    result = await handle_set_xml(ip_list, 'appcfg', 'whitelist')
    all_results.extend(result.details)
    await asyncio.sleep(0.5)
    
    logger.info("[2.5/5] Clear existing whitelist/blacklist")
    result = await clear_whitelist_blacklist(ip_list)
    all_results.extend(result.details)
    await asyncio.sleep(0.5)
    
    logger.info(f"[3/5] SetBlackList (exception IPs: {len(exception_ips)})")
    if exception_ips and req.imsi:
        result = await handle_set_blacklist(exception_ips, req.imsi)
        all_results.extend(result.details)
    await asyncio.sleep(0.5)
    
    logger.info(f"[4/5] SetWhiteList (other IPs: {len(other_ips)})")
    if other_ips and req.imsi:
        result = await handle_set_whitelist(other_ips, req.imsi)
        all_results.extend(result.details)
    await asyncio.sleep(0.5)
    
    logger.info("[5/5] StartCell")
    result = await handle_start_cell(ip_list, db, req.mode, req.duration, req.imsi)
    all_results.extend(result.details)
    
    return CommandResponse(
        status="success",
        last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
        details=all_results
    )


async def execute_blacklist_mode(ip_list: list, req: CommandRequest, db: Session) -> CommandResponse:
    logger.info(f"[Blacklist Mode] Starting bundle execution for {len(ip_list)} IPs")
    
    channels = get_exception_ips(db)
    exception_ips = channels['exception_ips']
    other_ips = channels['other_ips']
    
    exception_ips = [ip for ip in exception_ips if ip in ip_list]
    other_ips = [ip for ip in other_ips if ip in ip_list]
    
    all_results = []
    
    logger.info("[1/5] SetUlPara")
    result = await handle_set_ulpara(ip_list)
    all_results.extend(result.details)
    await asyncio.sleep(0.5)
    
    logger.info("[2/5] SetAppCfgExt (blacklist)")
    result = await handle_set_xml(ip_list, 'appcfg', 'blacklist')
    all_results.extend(result.details)
    await asyncio.sleep(0.5)
    
    logger.info("[2.5/5] Clear existing whitelist/blacklist")
    result = await clear_whitelist_blacklist(ip_list)
    all_results.extend(result.details)
    await asyncio.sleep(0.5)
    
    logger.info(f"[3/5] SetBlackList (other IPs: {len(other_ips)})")
    if other_ips and req.imsi:
        result = await handle_set_blacklist(other_ips, req.imsi)
        all_results.extend(result.details)
    await asyncio.sleep(0.5)
    
    logger.info(f"[4/5] SetWhiteList (exception IPs: {len(exception_ips)})")
    if exception_ips and req.imsi:
        result = await handle_set_whitelist(exception_ips, req.imsi)
        all_results.extend(result.details)
    await asyncio.sleep(0.5)
    
    logger.info("[5/5] StartCell")
    result = await handle_start_cell(ip_list, db, req.mode, req.duration, req.imsi)
    all_results.extend(result.details)
    
    return CommandResponse(
        status="success",
        last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
        details=all_results
    )


async def execute_all_mode(ip_list: list, req: CommandRequest, db: Session) -> CommandResponse:
    logger.info(f"[All Mode] Starting bundle execution for {len(ip_list)} IPs")
    
    all_results = []
    
    logger.info("[1/5] SetUlPara")
    result = await handle_set_ulpara(ip_list)
    all_results.extend(result.details)
    await asyncio.sleep(0.5)
    
    logger.info("[2/5] SetAppCfgExt (all)")
    result = await handle_set_xml(ip_list, 'appcfg', 'all')
    all_results.extend(result.details)
    await asyncio.sleep(0.5)
    
    logger.info("[3/5] SetBlackList (empty)")
    result = await handle_set_blacklist(ip_list, "")
    all_results.extend(result.details)
    await asyncio.sleep(0.5)
    
    logger.info("[4/5] SetWhiteList (empty)")
    result = await handle_set_whitelist(ip_list, "")
    all_results.extend(result.details)
    await asyncio.sleep(0.5)
    
    logger.info("[5/5] StartCell")
    result = await handle_start_cell(ip_list, db, req.mode, req.duration, req.imsi)
    all_results.extend(result.details)
    
    return CommandResponse(
        status="success",
        last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
        details=all_results
    )

async def execute_df_mode(ip_list: list, req: CommandRequest, db: Session) -> CommandResponse:
    """
    Execute DF mode bundle:
    1. SetUlPara
    2. SetAppCfgExt (provider)
    3. SetCellPara (provider)
    4. SetBlackList (IMSI)
    5. GetCellPara
    6. StartCell
    """
    logger.info(f"[DF Mode] Starting bundle execution for {len(ip_list)} IPs with provider: {req.provider}")
    
    all_results = []
    
    logger.info("[1/6] SetUlPara")
    result = await handle_set_ulpara(ip_list)
    all_results.extend(result.details)
    await asyncio.sleep(0.5)
    
    logger.info(f"[2/6] SetAppCfgExt ({req.provider})")
    result = await handle_set_xml(ip_list, 'appcfg', req.provider)
    all_results.extend(result.details)
    await asyncio.sleep(0.5)
    
    logger.info(f"[3/6] SetCellPara ({req.provider})")
    result = await handle_set_xml(ip_list, 'cellpara', req.provider)
    all_results.extend(result.details)
    await asyncio.sleep(0.5)
    
    logger.info("[4/6] SetBlackList")
    if req.imsi:
        result = await handle_set_blacklist(ip_list, req.imsi)
        all_results.extend(result.details)
    await asyncio.sleep(0.5)
    
    logger.info("[5/6] GetCellPara")
    result = await handle_get_cellpara(ip_list, db)
    all_results.extend(result.details)
    await asyncio.sleep(0.5)
    
    logger.info("[6/6] StartCell")
    result = await handle_start_cell(ip_list, db, None, None, req.imsi)
    all_results.extend(result.details)
    
    return CommandResponse(
        status="success",
        last_checked=time.strftime("%Y-%m-%d %H:%M:%S"),
        details=all_results
    )
