"""
Campaign endpoints - Campaign management (List, Create, Detail, Update)
Tags: Campaign
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io

from app.db.database import get_db
from app.db.schemas import (
    CampaignCreate, CampaignUpdate, 
    CampaignListResponse, CampaignDetail
)
from app.service.campaign_service import (
    list_campaigns, create_campaign,
    get_campaign_detail, update_campaign_status
)
from app.service.export_service import generate_pdf, generate_excel

router = APIRouter()

@router.get("/campaign", response_model=CampaignListResponse, tags=["Campaign"])
def list_campaign(db: Session = Depends(get_db)):
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
    result = create_campaign(db, req.name, req.imsi, req.provider)
    
    if result["status"] == "success":
        return result
    
    raise HTTPException(status_code=400, detail=result["message"])


@router.get("/campaign/{campaign_id}/detail", response_model=CampaignDetail, tags=["Campaign"])
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
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
    result = update_campaign_status(db, campaign_id, req.status)
    
    if result["status"] == "success":
        return result
    
    raise HTTPException(status_code=404, detail=result["message"])


@router.get("/campaign/{campaign_id}/export/{export_type}", tags=["Campaign"])
def export_campaign(campaign_id: int, export_type: str, db: Session = Depends(get_db)):
    """
    Export campaign crawling data
    - export_type: "pdf" atau "excel"
    """
    if export_type not in ["pdf", "excel"]:
        raise HTTPException(status_code=400, detail="Export type harus 'pdf' atau 'excel'")
    
    try:
        if export_type == "pdf":
            pdf_bytes = generate_pdf(db, campaign_id)
            if not pdf_bytes:
                raise HTTPException(status_code=404, detail="Campaign tidak ditemukan")
            
            return StreamingResponse(
                io.BytesIO(pdf_bytes),
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename=campaign_{campaign_id}_crawling.pdf"}
            )
        
        else:  # excel
            excel_bytes = generate_excel(db, campaign_id)
            if not excel_bytes:
                raise HTTPException(status_code=404, detail="Campaign tidak ditemukan")
            
            return StreamingResponse(
                io.BytesIO(excel_bytes),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename=campaign_{campaign_id}_crawling.xlsx"}
            )
    
    except HTTPException:
        raise
    except Exception as e:
        print(f"Export error: {e}")
        raise HTTPException(status_code=500, detail=f"Error generating export: {str(e)}")
    

@router.post("/send_arfcn", tags=["Campaign"])
def send_arfcn(
    arfcn: int = Query(...),
    status: Optional[bool] = Query(None)
):
    print(f"Received ARFCN: {arfcn} STATUS : {status}")
    return {
        "status": "success",
        "message": "ARFCN received successfully",
        "data": {
            "arfcn": arfcn,
            "status": status
        }
    }