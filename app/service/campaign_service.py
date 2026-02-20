from typing import Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.database import SessionLocal
from app.db.models import Crawling, Campaign
from app.service.crawling_service import start_crawling
from app.service.wb_status_service import update_wb_status
from app.utils.logger import setup_logger
from app.service.log_service import add_log

logger = setup_logger("CAMPAIGN_SERVICE")

def list_campaigns(db: Session, mode: Optional[str] = None) -> Dict:
    query = db.query(
        Campaign, 
        func.count(Crawling.id).label("crawling_count")
    ).outerjoin(Crawling, Crawling.campaign_id == Campaign.id)
    
    if mode:
        query = query.filter(Campaign.mode == mode)
    
    query = query.order_by(
        Campaign.created_at.desc(), 
        Campaign.id.desc()
    ).group_by(Campaign.id)   
    
    campaign_results = query.all()
    
    result = []
    for campaign, crawling_count in campaign_results:
        result.append({
            "id": campaign.id,
            "name": campaign.name,
            "imsi": campaign.imsi,
            "provider": campaign.provider,
            "status": campaign.status,
            "mode": campaign.mode,
            "duration": campaign.duration,
            "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
            "start_scan": campaign.start_scan.isoformat() if campaign.start_scan else None,
            "stop_scan": campaign.stop_scan.isoformat() if campaign.stop_scan else None,
            "crawling_count": crawling_count
        })
    
    return {
        "status": "success",
        "message": f"Campaign list retrieved {'for mode: ' + mode if mode else 'for all'}",
        "data": result,
        "total": len(result)
    }

async def create_campaign(db: Session, name: str, imsi: str, provider: str, mode: str, duration: str = None) -> Dict:
    from datetime import datetime
    from app.db.schemas import CommandRequest
    
    db_imsi = imsi.strip().replace(' ', ',') if imsi else ""
    
    # Fetch all targets for initial target_info (Revision: user wants all targets)
    from app.db.models import Target
    all_targets = db.query(Target).all()
    target_info_list = []
    for target in all_targets:
        target_info_list.append({
            "name": target.name,
            "imsi": target.imsi,
            "alert_status": target.alert_status,
            "target_status": target.target_status
        })
    
    campaign = Campaign(
        name=name,
        imsi=db_imsi,
        provider=provider,
        mode=mode,
        duration=duration,
        status="started",
        start_scan=datetime.now(),
        target_info=target_info_list
    )
    
    try:
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        
        crawling_request = CommandRequest(
            mode=mode,
            imsi=imsi,
            provider=provider,
            duration=duration,
            ip=None
        )
        await start_crawling(req=crawling_request, db=db)
        add_log(db, f"Campaign '{name}' started", "info", "User")
        return {
            "status": "success",
            "message": "Campaign created and crawling started successfully",
            "data": {
                "id": campaign.id,
                "name": campaign.name,
                "imsi": campaign.imsi,
                "provider": campaign.provider,
                "mode": campaign.mode,
                "status": campaign.status,
                "duration": campaign.duration,
                "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
                "start_scan": campaign.start_scan.isoformat() if campaign.start_scan else None,
                "stop_scan": campaign.stop_scan.isoformat() if campaign.stop_scan else None
            },
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": f"Failed to create campaign: {str(e)}",
            "data": None
        }


def get_campaign_detail(db: Session, campaign_id: int) -> Dict:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    
    if not campaign:
        return {
            "status": "error",
            "message": f"Campaign with id {campaign_id} not found",
            "data": None
        }
    
    crawlings = db.query(Crawling).filter(
        Crawling.campaign_id == campaign_id
    ).all()
    
    # Build a lookup dict for target_info by IMSI
    target_info_map = {}
    if campaign.target_info:
        for target in campaign.target_info:
            if isinstance(target, dict) and 'imsi' in target:
                target_info_map[target['imsi']] = target
    
    crawling_data = []
    for c in crawlings:
        crawling_item = {
            "id": c.id,
            "timestamp": c.timestamp,
            "rsrp": c.rsrp,
            "taType": c.taType,
            "ulCqi": c.ulCqi,
            "ulRssi": c.ulRssi,
            "imsi": c.imsi,
            "ip": c.ip,
            "ch": c.ch,
            "provider": c.provider,
            "count": c.count if c.count is not None else 0,
        }
        
        # Add alert_status and alert_name if IMSI exists in target_info
        if c.imsi in target_info_map:
            target = target_info_map[c.imsi]
            crawling_item["alert_status"] = target.get("alert_status")
            crawling_item["alert_name"] = target.get("name")
        
        crawling_data.append(crawling_item)
    
    return {
        "status": "success",
        "message": "Campaign detail retrieved",
        "data": {
            "id": campaign.id,
            "name": campaign.name,
            "imsi": campaign.imsi,
            "provider": campaign.provider,
            "status": campaign.status,
            "mode": campaign.mode,
            "duration": campaign.duration,
            "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
            "start_scan": campaign.start_scan.isoformat() if campaign.start_scan else None,
            "stop_scan": campaign.stop_scan.isoformat() if campaign.stop_scan else None,
            "crawlings": crawling_data
        }
    }
    
def get_latest_campaign_id(db: Session) -> int:
    campaign = db.query(Campaign).order_by(Campaign.id.desc()).first()
    return campaign.id if campaign else None

async def stop_campaign(db: Session, campaign_id: int) -> Dict:
    from app.service.timer_service import get_timer_ops_instance
    from app.service.utils_service import get_all_ips_db
    from app.service.command_service import handle_stop_cell
    from datetime import datetime
    
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        logger.error(f"[StopCampaign] Campaign {campaign_id} not found")
        return {
            "status": "error",
            "message": "Campaign tidak ditemukan"
        }
    
    try:
        campaign.status = 'completed'
        campaign.stop_scan = datetime.now()
        db.commit()
        logger.info(f"[StopCampaign] Campaign {campaign_id} marked as completed")
        
        timer_ops = get_timer_ops_instance()
        timer_ops.stop_timer(campaign_id)
        logger.info(f"[StopCampaign] Timer stopped for campaign {campaign_id}")
        
        all_ips = get_all_ips_db(db)
        logger.info(f"[StopCampaign] Stopping cells for IPs: {all_ips}")
        
        await handle_stop_cell(all_ips)
        update_wb_status(db, False)
        
        add_log(db, f"Campaign '{campaign.name}' stopped", "info", "User")
        return {
            "status": "success",
            "message": f"Campaign {campaign_id} stopped successfully",
            "data": {}
        }
    except Exception as e:
        logger.error(f"[StopCampaign] Error stopping campaign {campaign_id}: {e}")
        return {
            "status": "error",
            "message": f"Failed to stop campaign: {str(e)}"
        }
