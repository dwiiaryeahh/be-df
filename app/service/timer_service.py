"""
Timer Service - Manages whitelist/blacklist timer operations for campaigns
"""
import asyncio
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models import Campaign, Target, Heartbeat, Operator
from app.service.utils_service import get_send_command_instance, provider_mapping
from app.utils.logger import setup_logger


class TimerOps:
    def __init__(self):
        self.active_timers: Dict[int, asyncio.Task] = {}  # campaign_id -> task
        self.is_running: Dict[int, bool] = {}  # campaign_id -> running status
        self.logger = setup_logger("timer_service")
        
    async def _wait_for_duration(self, seconds: float, campaign_id: int, start_time: float, total_duration: int) -> bool:
        """
        Returns True if duration expired or timer stopped, False if wait completed naturally.
        Checks every 1 second for higher responsiveness.
        """
        check_interval = 1.0
        iterations = int(seconds / check_interval)
        
        for _ in range(iterations):
            if not self.is_running.get(campaign_id, False):
                return True
            if time.time() - start_time >= total_duration:
                return True
            await asyncio.sleep(check_interval)
            
        # Handle decimal remainder
        remainder = seconds % check_interval
        if remainder > 0:
            if not self.is_running.get(campaign_id, False):
                return True
            if time.time() - start_time >= total_duration:
                return True
            await asyncio.sleep(remainder)
            
        return time.time() - start_time >= total_duration

    def parse_duration(self, duration_str: str) -> int:
        """
        Parse duration string in MM:SS format to total seconds
        Example: "05:00" -> 300 seconds, "20:10" -> 1210 seconds
        """
        try:
            parts = duration_str.split(":")
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = int(parts[1])
                return minutes * 60 + seconds
            return 0
        except:
            return 0
    
    def get_active_target_imsis(self, db: Session, campaign_id: int) -> List[str]:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign or not campaign.imsi:
            self.logger.warning(f"[Timer] No campaign found or no IMSI data for campaign {campaign_id}")
            return []
        
        imsis = [imsi.strip() for imsi in campaign.imsi.split(',') if imsi.strip()]
        
        all_targets = db.query(Target).all()
        
        target_info_list = []
        for target in all_targets:
            target_info_list.append({
                "name": target.name,
                "imsi": target.imsi,
                "alert_status": target.alert_status,
                "target_status": target.target_status
            })
        
        if target_info_list:
            campaign.target_info = target_info_list
            db.commit()
            self.logger.info(f"[Timer] Updated target_info for campaign {campaign_id} with {len(target_info_list)} targets (ALL DB targets)")
        
        self.logger.debug(f"[Timer] Retrieved {len(imsis)} IMSI(s) from campaign {campaign_id}: {imsis}")
        return imsis
    
    def get_exception_channels(self, db: Session, target_imsis: List[str]) -> Dict[str, List[str]]:
        """
        Get exception channels based on Operator table.
        Exception IPs: All IPs that exist in the Operator table
        Other IPs: All IPs that don't exist in the Operator table
        """
        exception_ips = []
        other_ips = []
        
        # Get all IPs from Operator table
        operator_ips = set()
        operators = db.query(Operator).all()
        for op in operators:
            if op.ip:
                operator_ips.add(op.ip)
        
        # Get all IPs from Heartbeat table
        heartbeats = db.query(Heartbeat).all()
        
        for hb in heartbeats:
            if hb.source_ip in operator_ips:
                exception_ips.append(hb.source_ip)
            else:
                other_ips.append(hb.source_ip)
        
        self.logger.debug(f"[Exception Channels] Exception IPs (from Operator table): {exception_ips}")
        self.logger.debug(f"[Exception Channels] Other IPs: {other_ips}")
        
        return {
            'exception_ips': exception_ips,
            'other_ips': other_ips
        }
    
    
    def stop_exception_channels(self, db: Session, target_imsis: List[str]):
        """Stop only exception channels where MCC+MNC matches target IMSI prefix"""
        from app.config.utils import StopCell
        
        channels = self.get_exception_channels(db, target_imsis)
        
        for ip in channels['exception_ips']:
            try:
                # Get operator info for this IP
                operator = db.query(Operator).filter(Operator.ip == ip).first()
                
                if operator and operator.mcc and operator.mnc:
                    # Construct 5-digit MCC+MNC prefix
                    mcc_mnc_prefix = f"{operator.mcc}{operator.mnc}"
                    
                    # Check if any target IMSI starts with this MCC+MNC
                    has_matching_target = any(imsi.startswith(mcc_mnc_prefix) for imsi in target_imsis)
                    
                    if has_matching_target:
                        get_send_command_instance().command(ip, StopCell)
                        self.logger.info(f"[Timer] StopCell on exception channel: {ip} (MCC+MNC: {mcc_mnc_prefix} matches target)")
                    else:
                        self.logger.debug(f"[Timer] Skipping StopCell on {ip} (MCC+MNC: {mcc_mnc_prefix} doesn't match any target)")
                else:
                    self.logger.warning(f"[Timer] No operator info found for IP {ip}, skipping stop")
                    
            except Exception as e:
                self.logger.error(f"Error stopping cell on {ip}: {e}")
    
    def start_exception_channels(self, db: Session, target_imsis: List[str]):
        """Start only exception channels where MCC+MNC matches target IMSI prefix"""
        from app.config.utils import StartCell
        
        channels = self.get_exception_channels(db, target_imsis)
        
        for ip in channels['exception_ips']:
            try:
                # Get operator info for this IP
                operator = db.query(Operator).filter(Operator.ip == ip).first()
                
                if operator and operator.mcc and operator.mnc:
                    # Construct 5-digit MCC+MNC prefix
                    mcc_mnc_prefix = f"{operator.mcc}{operator.mnc}"
                    
                    # Check if any target IMSI starts with this MCC+MNC
                    has_matching_target = any(imsi.startswith(mcc_mnc_prefix) for imsi in target_imsis)
                    
                    if has_matching_target:
                        get_send_command_instance().command(ip, StartCell)
                        self.logger.info(f"[Timer] StartCell on exception channel: {ip} (MCC+MNC: {mcc_mnc_prefix} matches target)")
                    else:
                        self.logger.debug(f"[Timer] Skipping StartCell on {ip} (MCC+MNC: {mcc_mnc_prefix} doesn't match any target)")
                else:
                    self.logger.warning(f"[Timer] No operator info found for IP {ip}, skipping start")
                    
            except Exception as e:
                self.logger.error(f"Error starting cell on {ip}: {e}")
    
    def stop_all_cells(self, db: Session):
        """Stop all cells"""
        from app.config.utils import StopCell
        from app.service.utils_service import get_all_ips_db
        
        all_ips = get_all_ips_db(db)
        for ip in all_ips:
            try:
                get_send_command_instance().command(ip, StopCell)
                self.logger.info(f"[Timer] StopCell on {ip}")
            except Exception as e:
                self.logger.error(f"Error stopping cell on {ip}: {e}")
    
    async def _simple_timer_cycle(self, campaign_id: int, mode: str, duration_seconds: int, initial_elapsed: float = 0):
        """Simple timer for 'all' and 'df' modes - just countdown and auto-stop"""
        db = SessionLocal()
        try:
            # Adjust start time if resuming
            start_time = time.time() - initial_elapsed
            self.is_running[campaign_id] = True
            
            remaining = duration_seconds - initial_elapsed
            if remaining <= 0:
                # Should have been caught before calling this, but safety check
                self.logger.info(f"[Timer] Simple timer already expired (elapsed: {initial_elapsed}s)")
                return

            self.logger.info(f"[Timer] Starting simple timer for campaign {campaign_id}, mode: {mode}, duration: {duration_seconds}s (elapsed: {initial_elapsed}s)")
            
            # Wait for remaining duration
            expired = await self._wait_for_duration(remaining, campaign_id, start_time, duration_seconds)
            
            if expired and self.is_running.get(campaign_id, False):
                self.logger.info(f"[Timer] Duration expired for campaign {campaign_id}. Stopping all cells...")
                self.stop_all_cells(db)
                
                campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if campaign:
                    campaign.status = 'completed'
                    campaign.stop_scan = datetime.now()
                    db.commit()
                    self.logger.info(f"[Timer] Campaign {campaign_id} marked as completed")
            
            self.logger.info(f"[Timer] Simple timer completed for campaign {campaign_id}")
            
        except Exception as e:
            self.logger.error(f"[Timer] Error in simple timer cycle for campaign {campaign_id}: {e}")
        finally:
            self.is_running[campaign_id] = False
            if campaign_id in self.active_timers:
                del self.active_timers[campaign_id]
            db.close()
    
    async def _timer_cycle(self, campaign_id: int, mode: str, duration_seconds: int, initial_elapsed: float = 0):
        """Timer cycle for whitelist/blacklist modes with cycling logic"""
        db = SessionLocal()
        try:
            start_time = time.time() - initial_elapsed
            self.is_running[campaign_id] = True
            
            # Get active target IMSIs from campaign's imsi field
            target_imsis = self.get_active_target_imsis(db, campaign_id)
            if not target_imsis:
                self.logger.warning(f"[Timer] No active targets found for campaign {campaign_id}")
                return
            
            self.logger.info(f"[Timer] Starting timer for campaign {campaign_id}, mode: {mode}, duration: {duration_seconds}s (elapsed: {initial_elapsed}s)")
            self.logger.debug(f"[Timer] Active target IMSIs: {target_imsis}")
            
            # Phase 1: Initial run for 2 minutes (120 seconds) -- 0 to 120s
            phase1_end = 120
            if initial_elapsed < phase1_end:
                remaining = phase1_end - initial_elapsed
                self.logger.info(f"[Timer] Phase 1: Running for {remaining:.1f} seconds...")
                
                if await self._wait_for_duration(remaining, campaign_id, start_time, duration_seconds):
                    if time.time() - start_time >= duration_seconds:
                        self.logger.info(f"[Timer] Duration expired during Phase 1 for campaign {campaign_id}")
                        self.stop_all_cells(db)
                        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                        if campaign:
                            campaign.status = 'completed'
                            campaign.stop_scan = datetime.now()
                            db.commit()
                    return
            
            # Phase 2: Stop for 5 minutes (300 seconds) -- 120 to 420s
            phase2_end = 120 + 300
            if initial_elapsed < phase2_end:
                # Refresh target IMSIs to get latest data
                target_imsis = self.get_active_target_imsis(db, campaign_id)
                
                # If we skipped Phase 1, use current elapsed as base, otherwise start from Phase 1 end
                start_of_phase = max(initial_elapsed, phase1_end)
                remaining = phase2_end - start_of_phase
                
                self.logger.info(f"[Timer] Phase 2: Stopping exception channels for {remaining:.1f} seconds...")
                self.logger.info(f"[Timer] Phase 2 -> Target IMSIS : {target_imsis}")
                self.stop_exception_channels(db, target_imsis)
                
                if await self._wait_for_duration(remaining, campaign_id, start_time, duration_seconds):
                    if time.time() - start_time >= duration_seconds:
                        self.logger.info(f"[Timer] Duration expired during Phase 2 for campaign {campaign_id}")
                        self.stop_all_cells(db)
                        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                        if campaign:
                            campaign.status = 'completed'
                            campaign.stop_scan = datetime.now()
                            db.commit()
                    return
            
            # Phase 3: Run for 30 seconds -- 420 to 450s
            phase3_end = 420 + 30
            if initial_elapsed < phase3_end:
                # Refresh target IMSIs to get latest data
                target_imsis = self.get_active_target_imsis(db, campaign_id)
                
                start_of_phase = max(initial_elapsed, phase2_end)
                remaining = phase3_end - start_of_phase
                
                self.logger.info(f"[Timer] Phase 3: Starting exception channels for {remaining:.1f} seconds...")
                self.logger.info(f"[Timer] Phase 3 -> Target IMSIS : {target_imsis}")
                self.start_exception_channels(db, target_imsis)
                
                if await self._wait_for_duration(remaining, campaign_id, start_time, duration_seconds):
                    if time.time() - start_time >= duration_seconds:
                        self.logger.info(f"[Timer] Duration expired during Phase 3 for campaign {campaign_id}")
                        self.stop_all_cells(db)
                        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                        if campaign:
                            campaign.status = 'completed'
                            campaign.stop_scan = datetime.now()
                            db.commit()
                    return
            
            # Phase 4: Cycle (30 sec run -> 5 min stop) until duration expires
            self.logger.info("[Timer] Phase 4: Entering cycle mode (30s run -> 5min stop)...")
            
            # If resuming directly into cycling, we rely on the loop.
            # But wait, Cycle starts with Stop (Wait 300s).
            # If we resume at 500s (Phase 4 + 50s).
            # The loop structure is: Stop(300s) -> Start(30s).
            # We strictly restart the cycle from the top if we reach here.
            # This is acceptable because determining exact sub-phase in cycle is overkill.
            # We just restart the cycle: Stop 5m -> Start 30s.
            
            while self.is_running.get(campaign_id, False):
                # Refresh target IMSIs at the beginning of each cycle to get latest data
                target_imsis = self.get_active_target_imsis(db, campaign_id)
                
                # Stop for 5 minutes
                self.logger.info("[Timer] Cycle: Stopping exception channels for 5 minutes...")
                self.logger.info(f"[Timer] Cycle STOP 5 Min -> Target IMSIS : {target_imsis}")
                self.stop_exception_channels(db, target_imsis)
                
                if await self._wait_for_duration(300, campaign_id, start_time, duration_seconds):
                    if time.time() - start_time >= duration_seconds:
                        self.logger.info(f"[Timer] Duration expired during Cycle Stop for campaign {campaign_id}")
                        self.stop_all_cells(db)
                        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                        if campaign:
                            campaign.status = 'completed'
                            campaign.stop_scan = datetime.now()
                            db.commit()
                    break
                
                # Refresh again before starting (in case it was updated during the 5-minute stop)
                target_imsis = self.get_active_target_imsis(db, campaign_id)
                
                # Start for 30 seconds
                self.logger.info("[Timer] Cycle: Starting exception channels for 30 seconds...")
                self.logger.info(f"[Timer] Cycle START 30 sec -> Target IMSIS : {target_imsis}")
                self.start_exception_channels(db, target_imsis)
                
                if await self._wait_for_duration(30, campaign_id, start_time, duration_seconds):
                    if time.time() - start_time >= duration_seconds:
                        self.logger.info(f"[Timer] Duration expired during Cycle Run for campaign {campaign_id}")
                        self.stop_all_cells(db)
                        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
                        if campaign:
                            campaign.status = 'completed'
                            campaign.stop_scan = datetime.now()
                            db.commit()
                    break
            
            self.logger.info(f"[Timer] Timer cycle completed for campaign {campaign_id}")

            
        except Exception as e:
            self.logger.error(f"[Timer] Error in timer cycle for campaign {campaign_id}: {e}")
        finally:
            self.is_running[campaign_id] = False
            if campaign_id in self.active_timers:
                del self.active_timers[campaign_id]
            db.close()
    
    def start_timer(self, campaign_id: int, mode: str, duration: str, initial_elapsed: float = 0):
        """Start timer for campaign based on mode"""
        self.stop_timer(campaign_id)
        
        # Parse duration
        duration_seconds = self.parse_duration(duration)
        if duration_seconds <= 0:
            self.logger.error(f"[Timer] Invalid duration: {duration}")
            return
        
        mode_lower = mode.lower()
        if mode_lower in ['whitelist', 'blacklist']:
            coro = self._timer_cycle(campaign_id, mode, duration_seconds, initial_elapsed=initial_elapsed)
        elif mode_lower in ['all', 'df']:
            coro = self._simple_timer_cycle(campaign_id, mode, duration_seconds, initial_elapsed=initial_elapsed)
        else:
            self.logger.error(f"[Timer] Unknown mode: {mode}")
            return
        
        task = asyncio.create_task(coro)
        self.active_timers[campaign_id] = task
        self.logger.info(f"[Timer] Started timer for campaign {campaign_id}, mode: {mode}, duration: {duration} (initial elapsed: {initial_elapsed}s)")
    
    def stop_timer(self, campaign_id: int):
        """Stop timer for a campaign"""
        if campaign_id in self.is_running:
            self.is_running[campaign_id] = False
        
        if campaign_id in self.active_timers:
            task = self.active_timers[campaign_id]
            if not task.done():
                task.cancel()
            del self.active_timers[campaign_id]
            self.logger.info(f"[Timer] Stopped timer for campaign {campaign_id}")
    
    def recover_active_campaigns(self, db: Session):
        """Recover active campaigns after server restart"""
        # Active campaigns are those with status='started'
        active_campaigns = db.query(Campaign).filter(Campaign.status == 'started').all()
        self.logger.info(f"[Timer] Found {len(active_campaigns)} active campaigns to recover")
        
        for campaign in active_campaigns:
            try:
                if not campaign.start_scan or not campaign.duration:
                    self.logger.warning(f"[Timer] Campaign {campaign.id} missing start_scan or duration, skipping")
                    continue
                
                # Calculate elapsed time
                elapsed = (datetime.now() - campaign.start_scan).total_seconds()
                duration_seconds = self.parse_duration(campaign.duration)
                
                if elapsed >= duration_seconds:
                    # Expired while offline
                    self.logger.info(f"[Timer] Campaign {campaign.id} expired while offline (elapsed: {elapsed}s, duration: {duration_seconds}s). Marking complete.")
                    campaign.status = 'completed'
                    campaign.stop_scan = datetime.now()
                    db.commit()
                    self.stop_all_cells(db)
                else:
                    # Resume
                    remaining = duration_seconds - elapsed
                    self.logger.info(f"[Timer] Resuming campaign {campaign.id} (elapsed: {elapsed}s, remaining: {remaining}s)")
                    self.start_timer(campaign.id, campaign.mode, campaign.duration, initial_elapsed=elapsed)
            except Exception as e:
                self.logger.error(f"[Timer] Error recovering campaign {campaign.id}: {e}")

    def stop_all_timers(self):
        """Stop all active timers"""
        for campaign_id in list(self.active_timers.keys()):
            self.stop_timer(campaign_id)


_timer_ops_instance = None

def get_timer_ops_instance() -> TimerOps:
    """Get or create global TimerOps instance"""
    global _timer_ops_instance
    if _timer_ops_instance is None:
        _timer_ops_instance = TimerOps()
    return _timer_ops_instance
