"""
Target endpoints - Target management (List, Create, Update, Import)
Tags: Target
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.schemas import (
    TargetCreate, TargetUpdate,
    TargetListResponse, TargetResponse,
    TargetImportResponse
)
from app.service.target_service import (
    list_targets, create_target,
    update_target, import_targets_from_xlsx
)

router = APIRouter()


@router.get("/target", response_model=TargetListResponse, tags=["Target"])
def get_target_list(db: Session = Depends(get_db)):
    """
    Get list of all targets
    """
    result = list_targets(db)
    
    if result["status"] == "success":
        return TargetListResponse(
            status="success",
            message=result["message"],
            data=result["data"],
            total=result["total"]
        )
    
    raise HTTPException(status_code=500, detail=result["message"])


@router.post("/target/create", response_model=TargetResponse, tags=["Target"])
def add_target(req: TargetCreate, db: Session = Depends(get_db)):
    """
    Add a new target
    """
    result = create_target(
        db,
        name=req.name,
        imsi=req.imsi,
        alert_status=req.alert_status,
        target_status=req.target_status
    )
    
    if result["status"] == "success":
        return TargetResponse(**result["data"])
    
    raise HTTPException(status_code=400, detail=result["message"])


@router.put("/target/{target_id}/update", response_model=TargetResponse, tags=["Target"])
def update_target_endpoint(target_id: int, req: TargetUpdate, db: Session = Depends(get_db)):
    """
    Update an existing target
    """
    result = update_target(
        db,
        target_id=target_id,
        name=req.name,
        imsi=req.imsi,
        alert_status=req.alert_status,
        target_status=req.target_status
    )
    
    if result["status"] == "success":
        return TargetResponse(**result["data"])
    
    raise HTTPException(status_code=404, detail=result["message"])


@router.post("/target/import", response_model=TargetImportResponse, tags=["Target"])
async def import_targets(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Import targets from XLSX file
    
    Expected XLSX format:
    - Column 1: name (required)
    - Column 2: imsi (required)
    - Column 3: alert_status (optional)
    - Column 4: target_status (optional)
    
    First row should be headers.
    """
    # Validate file extension
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(
            status_code=400,
            detail="File must be an Excel file (.xlsx or .xls)"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Import targets
        result = import_targets_from_xlsx(db, file_content)
        
        if result["status"] == "success":
            return TargetImportResponse(
                status="success",
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
