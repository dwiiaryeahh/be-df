"""
Campaign endpoints - Campaign management (List, Create, Detail, Update)
Tags: Campaign
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.schemas import (
    CampaignCreate, CampaignUpdate, 
    CampaignListResponse, CampaignDetail
)
from app.service.services import (
    list_campaigns, create_campaign,
    get_campaign_detail, update_campaign_status
)

router = APIRouter()


@router.get("/campaign", response_model=CampaignListResponse, tags=["Campaign"])
def list_campaign(db: Session = Depends(get_db)):
    """
    List semua campaign yang ada
    """
    result = list_campaigns(db)
    
    if result["status"] == "success":
        return CampaignListResponse(
            status="success",
            message=result["message"],
            data=result["data"],
            total=result["total"]
        )
    
    raise HTTPException(status_code=500, detail=result["message"])


@router.post("/campaign/start", tags=["Campaign"])
def campaign_start(req: CampaignCreate, db: Session = Depends(get_db)):
    """
    Create campaign baru (seperti start scan)
    
    Parameters:
    - name: Nama campaign
    - imsi: IMSI untuk scanning
    - provider: Provider/Operator
    """
    result = create_campaign(db, req.name, req.imsi, req.provider)
    
    if result["status"] == "success":
        return result
    
    raise HTTPException(status_code=400, detail=result["message"])


@router.get("/campaign/{campaign_id}/detail", response_model=CampaignDetail, tags=["Campaign"])
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """
    Get detail campaign dengan list crawling data
    
    Parameters:
    - campaign_id: ID campaign yang ingin dilihat
    """
    result = get_campaign_detail(db, campaign_id)
    
    if result["status"] == "success":
        data = result["data"]
        return CampaignDetail(
            id=data["id"],
            name=data["name"],
            imsi=data["imsi"],
            provider=data["provider"],
            status=data["status"],
            created_at=data["created_at"],
            crawlings=data["crawlings"]
        )
    
    raise HTTPException(status_code=404, detail=result["message"])


@router.put("/campaign/{campaign_id}/stop", tags=["Campaign"])
def campaign_stop(campaign_id: int, req: CampaignUpdate, db: Session = Depends(get_db)):
    """
    Update campaign status (misal: dari started -> stopped)
    
    Parameters:
    - campaign_id: ID campaign yang ingin diupdate
    - status: Status baru (started, stopped, completed, failed)
    """
    result = update_campaign_status(db, campaign_id, req.status)
    
    if result["status"] == "success":
        return result
    
    raise HTTPException(status_code=404, detail=result["message"])
