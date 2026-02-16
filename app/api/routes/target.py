"""
Target endpoints - Target management (List, Create, Update, Import)
Tags: Target
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.schemas import (
    TargetCreate, TargetUpdate,
    TargetListResponse, TargetResponse,
    TargetImportResponse,TargetSingleResponse
)
from app.service.target_service import (
    list_targets, create_target,
    update_target, import_targets_from_xlsx,
    delete_target
)

router = APIRouter()

@router.get("/target", response_model=TargetListResponse, tags=["Target"])
def get_target_list(target_status: Optional[str] = None, db: Session = Depends(get_db)):
    result = list_targets(db, target_status=target_status)
    
    if result["status"] == "success":
        return TargetListResponse(
            status=result["status"],
            message=result["message"],
            data=result["data"],
            total=result["total"]
        )
    
    raise HTTPException(status_code=500, detail=result["message"])


@router.post("/target/create", response_model=TargetSingleResponse, tags=["Target"])
async def add_target(req: TargetCreate, db: Session = Depends(get_db)):
    result = await create_target(
        db,
        name=req.name,
        imsi=req.imsi,
        alert_status=req.alert_status,
        target_status=req.target_status,
        campaign_id=req.campaign_id
    )
    
    if result["status"] == "success":
        return TargetSingleResponse(
            status=result["status"],
            message=result["message"],
            data=result["data"]
        )
    
    raise HTTPException(status_code=400, detail=result["message"])


@router.put("/target/{target_id}/update", response_model=TargetSingleResponse, tags=["Target"])
def update_target_endpoint(target_id: int, req: TargetUpdate, db: Session = Depends(get_db)):
    result = update_target(
        db,
        target_id=target_id,
        name=req.name,
        imsi=req.imsi,
        alert_status=req.alert_status,
        target_status=req.target_status
    )
    
    if result["status"] == "success":
        return TargetSingleResponse(
            status=result["status"],
            message=result["message"],
            data=result["data"]
        )
    
    raise HTTPException(status_code=404, detail=result["message"])


@router.delete("/target/{target_id}/delete", response_model=TargetSingleResponse, tags=["Target"])
def delete_target_endpoint(target_id: int, db: Session = Depends(get_db)):
    result = delete_target(db, target_id)
    
    if result["status"] == "success":
        return TargetSingleResponse(
            status=result["status"],
            message=result["message"],
            data=result["data"]
        )
    
    raise HTTPException(status_code=404, detail=result["message"])


@router.post("/target/import", response_model=TargetImportResponse, tags=["Target"])
async def import_targets(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="File must be an Excel file (.xlsx or .xls)"
        )
    
    try:
        file_content = await file.read()
        result = import_targets_from_xlsx(db, file_content)
        
        if result["status"] == "success":
            return TargetImportResponse(
                status=result["status"],
                message=result["message"],
                imported=result["imported"],
                failed=result["failed"],
                errors=result["errors"]
            )
        
        raise HTTPException(status_code=400, detail=result["message"])
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
