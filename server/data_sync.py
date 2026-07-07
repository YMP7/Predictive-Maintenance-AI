import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Callable

logger = logging.getLogger("DigitalTwin")

class DataSyncManager:
    def __init__(self):
        self.subscribers = {}
        self.last_update = {}
        self.update_interval = 2  # seconds
    
    def subscribe(self, channel: str, callback: Callable):
        if channel not in self.subscribers:
            self.subscribers[channel] = []
        self.subscribers[channel].append(callback)
    
    def publish(self, channel: str, data: Dict):
        self.last_update[channel] = {
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        for callback in self.subscribers.get(channel, []):
            try:
                callback(data)
            except Exception as e:
                logger.error("Error in data sync callback: %s", e)
    
    async def start_sync_loop(self, service):
        while True:
            try:
                summary = service.get_dashboard_summary()
                self.publish("dashboard", summary)
                
                statuses = service.get_all_machines_status()
                for status in statuses:
                    self.publish(f"machine:{status['machine_id']}", status)
                
                await asyncio.sleep(self.update_interval)
            except Exception as e:
                logger.error("Error in sync loop: %s", e)
                await asyncio.sleep(1)

_sync_manager = None

def get_sync_manager():
    global _sync_manager
    if _sync_manager is None:
        _sync_manager = DataSyncManager()
    return _sync_manager
