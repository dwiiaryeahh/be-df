from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.models import Target
from typing import Dict, Any
import openpyxl
from io import BytesIO
from app.utils.logger import setup_logger
from app.service.log_service import add_log

logger = setup_logger("[TARGET SERVICE]")

async def stop_exeption_ip(db: Session, target_imsi: str):
    from app.db.models import Operator
    from sqlalchemy import func
    
    target_mcc = target_imsi[:3]
    target_mnc = target_imsi[3:5]
    
    matching_operators = db.query(Operator).filter(
        func.concat(Operator.mcc, Operator.mnc) == f"{target_mcc}{target_mnc}",
        Operator.ip.isnot(None)
    ).all()
    
    if not matching_operators:
        print(f"[Target Service] No matching operators found for MCC+MNC: {target_mcc}{target_mnc}")
        return
    
    matching_ips = [op.ip for op in matching_operators]
        
    from app.service.command_service import handle_stop_cell
    await handle_stop_cell(matching_ips)
    
    logger.info(f"[Target Service] StopCell - Add Target {len(matching_ips)} exception channels")


def list_targets(db: Session, target_status: str = None) -> Dict[str, Any]:
    try:
        query = db.query(Target).order_by(Target.created_at.desc())
        
        if target_status:
            query = query.filter(Target.target_status == target_status)
        
        targets = query.all()
        
        target_list = []
        for target in targets:
            target_list.append({
                "id": target.id,
                "name": target.name,
                "imsi": target.imsi,
                "alert_status": target.alert_status,
                "target_status": target.target_status,
                "created_at": target.created_at.isoformat() if target.created_at else "",
                "updated_at": target.updated_at.isoformat() if target.updated_at else ""
            })
        
        message = "Targets retrieved successfully"
        if target_status:
            message = f"Targets with status '{target_status}' retrieved successfully"
        
        return {
            "status": "success",
            "message": message,
            "data": target_list,
            "total": len(target_list)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error retrieving targets: {str(e)}",
            "data": [],
            "total": 0
        }


async def create_target(db: Session, name: str, imsi: str, alert_status: str = None, target_status: str = None, campaign_id: int = None) -> Dict[str, Any]:
    try:
        existing_target = db.query(Target).filter(Target.imsi == imsi).first()
        if existing_target:
            return {
                "status": "error",
                "message": f"Target with IMSI {imsi} already exists"
            }
        
        new_target = Target(
            name=name,
            imsi=imsi,
            alert_status=alert_status,
            target_status=target_status
        )
        
        db.add(new_target)
        db.commit()
        db.refresh(new_target)
        
        await stop_exeption_ip(db, imsi)        
        if campaign_id:
            from app.db.models import Campaign
            from app.service.utils_service import get_exception_ips
            from app.service.command_service import handle_set_blacklist, handle_set_whitelist
            import asyncio
            
            campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if campaign and campaign.status == "started":
                all_targets = db.query(Target).all()
                target_info_list = []
                for target in all_targets:
                    target_info_list.append({
                        "name": target.name,
                        "imsi": target.imsi,
                        "alert_status": target.alert_status,
                        "target_status": target.target_status
                    })
                campaign.target_info = target_info_list
                
                active_targets = db.query(Target).filter(Target.target_status == 'Active').all()
                active_imsis = [t.imsi for t in active_targets]
                campaign.imsi = ",".join(active_imsis)
                db.commit()
                
                channels = get_exception_ips(db)
                exception_ips = channels.get('exception_ips', [])
                other_ips = channels.get('other_ips', [])
                
                all_imsis_str = campaign.imsi.replace(',', ' ')
                mode = campaign.mode.lower() if campaign.mode else ""
                
                async def execute_commands():
                    if mode == "whitelist":
                        if exception_ips:
                            await handle_set_blacklist(exception_ips, all_imsis_str)
                        if other_ips:
                            await handle_set_whitelist(other_ips, all_imsis_str)
                    elif mode == "blacklist":
                        if other_ips:
                            await handle_set_blacklist(other_ips, all_imsis_str)
                        if exception_ips:
                            await handle_set_whitelist(exception_ips, all_imsis_str)
                
                if mode in ["whitelist", "blacklist"]:
                    await execute_commands()
        
        add_log(db, f"Target '{name}' created", "info", "User")
        return {
            "status": "success",
            "message": "Target created successfully",
            "data": {
                "id": new_target.id,
                "name": new_target.name,
                "imsi": new_target.imsi,
                "alert_status": new_target.alert_status,
                "target_status": new_target.target_status,
                "created_at": new_target.created_at.isoformat() if new_target.created_at else "",
                "updated_at": new_target.updated_at.isoformat() if new_target.updated_at else ""
            }
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": f"Error creating target: {str(e)}"
        }


def update_target(db: Session, target_id: int, name: str = None, imsi: str = None, alert_status: str = None, target_status: str = None) -> Dict[str, Any]:
    try:
        target = db.query(Target).filter(Target.id == target_id).first()
        
        if not target:
            return {
                "status": "error",
                "message": f"Target with ID {target_id} not found"
            }
        
        # Check if new IMSI already exists (if IMSI is being updated)
        if imsi and imsi != target.imsi:
            existing_target = db.query(Target).filter(Target.imsi == imsi).first()
            if existing_target:
                return {
                    "status": "error",
                    "message": f"Target with IMSI {imsi} already exists"
                }
        
        # Update fields if provided
        if name is not None:
            target.name = name
        if imsi is not None:
            target.imsi = imsi
        if alert_status is not None:
            target.alert_status = alert_status
        if target_status is not None:
            target.target_status = target_status
        
        # Update timestamp
        target.updated_at = func.now()
        
        db.commit()
        db.refresh(target)
        
        add_log(db, f"Target '{target.name}' updated", "info", "User")
        return {
            "status": "success",
            "message": "Target updated successfully",
            "data": {
                "id": target.id,
                "name": target.name,
                "imsi": target.imsi,
                "alert_status": target.alert_status,
                "target_status": target.target_status,
                "created_at": target.created_at.isoformat() if target.created_at else "",
                "updated_at": target.updated_at.isoformat() if target.updated_at else ""
            }
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": f"Error updating target: {str(e)}"
        }


def import_targets_from_xlsx(db: Session, file_content: bytes) -> Dict[str, Any]:
    """
    Import targets from XLSX file
    Expected columns: name, imsi, alert_status (optional), target_status (optional)
    """
    imported = 0
    failed = 0
    errors = []
    
    try:
        # Load workbook from bytes
        workbook = openpyxl.load_workbook(BytesIO(file_content))
        sheet = workbook.active
        
        # Get header row (assuming first row is header)
        headers = []
        for cell in sheet[1]:
            headers.append(cell.value.lower() if cell.value else "")
        
        # Validate required columns
        if "name" not in headers or "imsi" not in headers:
            return {
                "status": "error",
                "message": "XLSX file must contain 'name' and 'imsi' columns",
                "imported": 0,
                "failed": 0,
                "errors": ["Missing required columns: name and/or imsi"]
            }
        
        # Get column indices
        name_idx = headers.index("name")
        imsi_idx = headers.index("imsi")
        alert_status_idx = headers.index("alert_status") if "alert_status" in headers else None
        target_status_idx = headers.index("target_status") if "target_status" in headers else None
        
        # Process each row (skip header)
        for row_num, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            try:
                name = row[name_idx]
                imsi = row[imsi_idx]
                
                # Skip empty rows
                if not name or not imsi:
                    continue
                
                # Convert to string
                name = str(name).strip()
                imsi = str(imsi).strip()
                
                alert_status = str(row[alert_status_idx]).strip() if alert_status_idx is not None and row[alert_status_idx] else None
                target_status = str(row[target_status_idx]).strip() if target_status_idx is not None and row[target_status_idx] else None
                
                # Check if IMSI already exists
                existing_target = db.query(Target).filter(Target.imsi == imsi).first()
                if existing_target:
                    errors.append(f"Row {row_num}: IMSI {imsi} already exists")
                    failed += 1
                    continue
                
                # Create new target
                new_target = Target(
                    name=name,
                    imsi=imsi,
                    alert_status=alert_status,
                    target_status=target_status
                )
                
                db.add(new_target)
                imported += 1
                
            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")
                failed += 1
        
        # Commit all changes
        db.commit()
        add_log(db, f"Imported {imported} targets from XLSX", "info", "User")
        return {
            "status": "success",
            "message": f"Import completed: {imported} imported, {failed} failed",
            "imported": imported,
            "failed": failed,
            "errors": errors
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": f"Error importing XLSX: {str(e)}",
            "imported": 0,
            "failed": 0,
            "errors": [str(e)]
        }


def delete_target(db: Session, target_id: int) -> Dict[str, Any]:
    """
    Delete a target by ID
    """
    try:
        target = db.query(Target).filter(Target.id == target_id).first()
        
        if not target:
            return {
                "status": "error",
                "message": f"Target with ID {target_id} not found"
            }
        
        # Store data for the response before deleting
        target_data = {
            "id": target.id,
            "name": target.name,
            "imsi": target.imsi,
            "alert_status": target.alert_status,
            "target_status": target.target_status,
            "created_at": target.created_at.isoformat() if target.created_at else "",
            "updated_at": target.updated_at.isoformat() if target.updated_at else ""
        }
        
        db.delete(target)
        db.commit()
        
        add_log(db, f"Target '{target.name}' deleted", "info", "User")
        return {
            "status": "success",
            "message": "Target deleted successfully",
            "data": target_data
        }
    except Exception as e:
        db.rollback()
        return {
            "status": "error",
            "message": f"Error deleting target: {str(e)}"
        }
