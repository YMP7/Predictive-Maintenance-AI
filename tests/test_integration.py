import pytest
import time
from data_service import get_data_service

class TestDataServiceIntegration:
    def test_simulation_start_stop(self):
        service = get_data_service()
        
        # Start simulation
        service.start_simulation(interval=0.1)
        assert service.is_running is True
        
        # Wait for data to collect
        time.sleep(0.5)
        
        # Check data collected
        summary = service.get_dashboard_summary()
        assert summary["total_machines"] > 0
        
        # Check cache
        telemetry = service.get_machine_telemetry("M001", limit=10)
        assert len(telemetry) > 0
        
        # Stop simulation
        service.stop_simulation()
        assert service.is_running is False
        
    def test_machine_status_retrieval(self):
        service = get_data_service()
        service.start_simulation(interval=0.1)
        
        time.sleep(0.5)
        
        status = service.get_machine_status("M001")
        assert status is not None
        assert "status" in status
        assert "rul_days" in status
        assert "machine_info" in status
        
        service.stop_simulation()
