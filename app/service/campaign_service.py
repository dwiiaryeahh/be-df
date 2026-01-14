from typing import Dict
from sqlalchemy.orm import Session
from app.db.models import Crawling, Campaign

def list_campaigns(db: Session) -> Dict:
    campaigns = db.query(Campaign).all()
    
    result = []
    for campaign in campaigns:
        crawling_count = db.query(Crawling).filter(
            Crawling.campaign_id == campaign.id
        ).count()
        
        result.append({
            "id": campaign.id,
            "name": campaign.name,
            "imsi": campaign.imsi,
            "provider": campaign.provider,
            "status": campaign.status,
            "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
            "crawling_count": crawling_count
        })
    
    return {
        "status": "success",
        "message": "Campaign list retrieved",
        "data": result,
        "total": len(result)
    }


def create_campaign(db: Session, name: str, imsi: str, provider: str) -> Dict:
    campaign = Campaign(
        name=name,
        imsi=imsi,
        provider=provider,
        status="started"
    )
    
    try:
        db.add(campaign)
        db.commit()
        db.refresh(campaign)
        
        return {
            "status": "success",
            "message": "Campaign created successfully",
            "data": {
                "id": campaign.id,
                "name": campaign.name,
                "imsi": campaign.imsi,
                "provider": campaign.provider,
                "status": campaign.status,
                "created_at": campaign.created_at.isoformat() if campaign.created_at else None
            }
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
    
    crawling_data = [
        {
            "id": c.id,
            "timestamp": c.timestamp,
            "rsrp": c.rsrp,
            "taType": c.taType,
            "ulCqi": c.ulCqi,
            "ulRssi": c.ulRssi,
            "imsi": c.imsi,
            "ip": c.ip
        }
        for c in crawlings
    ]
    
    return {
        "status": "success",
        "message": "Campaign detail retrieved",
        "data": {
            "id": campaign.id,
            "name": campaign.name,
            "imsi": campaign.imsi,
            "provider": campaign.provider,
            "status": campaign.status,
            "created_at": campaign.created_at.isoformat() if campaign.created_at else None,
            "crawlings": crawling_data
        }
    }


def update_campaign_status(db: Session, campaign_id: int, new_status: str) -> Dict:
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    
    if not campaign:
        return {
            "status": "error",
            "message": f"Campaign with id {campaign_id} not found",
            "data": None
        }
    
    try:
        campaign.status = new_status
        db.commit()
        db.refresh(campaign)
        
        return {
            "status": "success",
            "message": f"Campaign status updated to {new_status}",
            "data": {
                "id": campaign.id,
                "name": campaign.name,
                "imsi": campaign.imsi,
                "provider": campaign.provider,
                "status": campaign.status,
                "created_at": campaign.created_at.isoformat() if campaign.created_at else None
            }
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": f"Failed to update campaign: {str(e)}",
            "data": None
        }
    
def get_latest_campaign_id(db: Session) -> int:
    campaign = db.query(Campaign).order_by(Campaign.id.desc()).first()
    return campaign.id if campaign else None
