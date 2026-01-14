"""
Event bus untuk WebSocket real-time streaming
Menerima data dari controller dan broadcast ke websocket clients
"""
import asyncio
from typing import Dict, List, Callable, Set
from fastapi import WebSocketDisconnect

class EventBus:
    def __init__(self):
        """Initialize event bus dengan subscription management"""
        self.heartbeat_subscribers: Set[tuple] = set()  # Set of (id, callback)
        self.crawling_subscribers: Set[tuple] = set()
        self.sniffing_subscribers: Set[tuple] = set()
        self._next_id = 0
    
    def _get_next_id(self) -> int:
        """Get unique ID untuk subscriber"""
        self._next_id += 1
        return self._next_id
    
    def subscribe_heartbeat(self, callback: Callable) -> int:
        """Subscribe untuk menerima heartbeat data, return subscriber ID"""
        sub_id = self._get_next_id()
        self.heartbeat_subscribers.add((sub_id, callback))
        return sub_id
    
    def unsubscribe_heartbeat(self, sub_id: int):
        """Unsubscribe dari heartbeat events"""
        self.heartbeat_subscribers = {(sid, cb) for sid, cb in self.heartbeat_subscribers if sid != sub_id}
    
    def subscribe_crawling(self, callback: Callable) -> int:
        """Subscribe untuk menerima crawling data, return subscriber ID"""
        sub_id = self._get_next_id()
        self.crawling_subscribers.add((sub_id, callback))
        return sub_id
    
    def unsubscribe_crawling(self, sub_id: int):
        """Unsubscribe dari crawling events"""
        self.crawling_subscribers = {(sid, cb) for sid, cb in self.crawling_subscribers if sid != sub_id}
    
    def subscribe_sniffing(self, callback: Callable) -> int:
        """Subscribe untuk menerima sniffing data, return subscriber ID"""
        sub_id = self._get_next_id()
        self.sniffing_subscribers.add((sub_id, callback))
        return sub_id
    
    def unsubscribe_sniffing(self, sub_id: int):
        """Unsubscribe dari sniffing events"""
        self.sniffing_subscribers = {(sid, cb) for sid, cb in self.sniffing_subscribers if sid != sub_id}
    
    async def send_heartbeat(self, data: Dict):
        """Broadcast heartbeat data ke semua subscribers"""
        dead_subs = []
        for sub_id, callback in self.heartbeat_subscribers:
            try:
                await callback(data)
            except (WebSocketDisconnect, RuntimeError) as e:
                # Connection closed, mark for removal
                if "close message" in str(e) or isinstance(e, WebSocketDisconnect):
                    dead_subs.append(sub_id)
            except Exception as e:
                print(f"[ERROR] heartbeat callback error: {e}")
        
        # Remove dead subscriptions
        for sub_id in dead_subs:
            self.unsubscribe_heartbeat(sub_id)
    
    async def send_crawling(self, data: Dict):
        """Broadcast crawling data ke semua subscribers"""
        dead_subs = []
        for sub_id, callback in self.crawling_subscribers:
            try:
                await callback(data)
            except (WebSocketDisconnect, RuntimeError) as e:
                if "close message" in str(e) or isinstance(e, WebSocketDisconnect):
                    dead_subs.append(sub_id)
            except Exception as e:
                print(f"[ERROR] crawling callback error: {e}")
        
        for sub_id in dead_subs:
            self.unsubscribe_crawling(sub_id)
    
    async def send_sniffing(self, data: Dict):
        """Broadcast sniffing data ke semua subscribers"""
        dead_subs = []
        for sub_id, callback in self.sniffing_subscribers:
            try:
                await callback(data)
            except (WebSocketDisconnect, RuntimeError) as e:
                if "close message" in str(e) or isinstance(e, WebSocketDisconnect):
                    dead_subs.append(sub_id)
            except Exception as e:
                print(f"[ERROR] sniffing callback error: {e}")
        
        for sub_id in dead_subs:
            self.unsubscribe_sniffing(sub_id)


# Global event bus instance
event_bus = EventBus()
