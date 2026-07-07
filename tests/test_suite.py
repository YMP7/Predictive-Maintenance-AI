import pytest
from sensor_simulator import SensorSimulator, MultiMachineSimulator
from ai_agent import AlertGenerator, FaultDetector, RULEstimator, AIAgent

class TestSensorSimulator:
    def test_simulator_initialization(self):
        sim = SensorSimulator("M001", "normal")
        assert sim.machine_id == "M001"
        assert sim.fault_mode == "normal"
    
    def test_sensor_reading_generation(self):
        sim = SensorSimulator("M001", "normal")
        reading = sim.get_sensor_reading()
        
        assert "timestamp" in reading
        assert "vibration" in reading
        assert "temperature" in reading
        assert "current" in reading
        assert "status" in reading
        
        assert "rms" in reading["vibration"]
        assert isinstance(reading["temperature"], (int, float))
        assert isinstance(reading["current"], (int, float))

class TestFaultDetector:
    def test_normal_operation(self):
        detector = FaultDetector()
        reading = {
            "machine_id": "M001",
            "vibration": {"x": 0.3, "y": 0.4, "z": 0.2, "rms": 0.5},
            "temperature": 50.0,
            "current": 2.5
        }
        fault_type, issues = detector.detect_fault(reading)
        assert fault_type == "Normal"
        assert len(issues) == 0
    
    def test_critical_vibration(self):
        detector = FaultDetector()
        reading = {
            "machine_id": "M001",
            "vibration": {"x": 2.5, "y": 2.0, "z": 1.5, "rms": 3.5},
            "temperature": 50.0,
            "current": 2.5
        }
        fault_type, issues = detector.detect_fault(reading)
        assert fault_type != "Normal"
        assert any("Critical" in issue for issue in issues)

class TestRULEstimator:
    def test_insufficient_data(self):
        estimator = RULEstimator()
        rul_info = estimator.estimate_rul("M001")
        assert rul_info["status"] == "Insufficient Data"
        assert rul_info["rul_days"] is None
        
    def test_sufficient_data(self):
        estimator = RULEstimator()
        # Feed 11 normal readings
        for i in range(11):
            reading = {
                "vibration": {"rms": 0.5 + i * 0.01},
                "temperature": 45.0 + i * 0.5,
                "current": 2.2 + i * 0.05
            }
            estimator.update_degradation("M001", reading)
            
        rul_info = estimator.estimate_rul("M001")
        assert rul_info["status"] != "Insufficient Data"
        assert rul_info["rul_days"] is not None

    def test_history_is_bounded(self):
        estimator = RULEstimator()
        estimator.max_history = 3
        reading = {
            "vibration": {"rms": 0.5},
            "temperature": 45.0,
            "current": 2.2,
        }
        for _ in range(5):
            estimator.update_degradation("M001", reading)

        assert len(estimator.history["M001"]) == 3


class StubRULEstimator:
    def __init__(self, rul_days):
        self.rul_days = rul_days

    def estimate_rul(self, _machine_id):
        return {"rul_days": self.rul_days, "confidence": 0.9, "status": "Degrading"}


class TestAlertGenerator:
    @pytest.mark.parametrize(
        ("rul_days", "expected_severity"),
        [(2, "Critical"), (5, "High"), (8, "Medium")],
    )
    def test_rul_alert_severity(self, rul_days, expected_severity):
        reading = {
            "machine_id": "M001",
            "vibration": {"rms": 0.5},
            "temperature": 50.0,
            "current": 2.5,
        }
        alerts = AlertGenerator().generate_alerts(
            "M001",
            FaultDetector(),
            StubRULEstimator(rul_days),
            reading,
        )

        assert alerts[0]["type"] == "RUL Warning"
        assert alerts[0]["severity"] == expected_severity

class TestAIAgent:
    def test_agent_initialization(self):
        agent = AIAgent()
        assert agent.fault_detector is not None
        assert agent.rul_estimator is not None
        assert agent.alert_generator is not None
        
    def test_process_reading(self):
        agent = AIAgent()
        reading = {
            "machine_id": "M001",
            "vibration": {"rms": 0.5},
            "temperature": 50.0,
            "current": 2.5,
            "timestamp": "2026-06-04T12:00:00Z"
        }
        result = agent.process_reading(reading)
        assert result["machine_id"] == "M001"
        assert "status" in result
        assert "rul_days" in result
        assert "recommendation" in result

    def test_process_reading_derives_status_and_caches_result(self):
        agent = AIAgent()
        reading = {
            "machine_id": "M001",
            "vibration": {"rms": 0.5},
            "temperature": 50.0,
            "current": 2.5,
            "status": "Critical",
        }

        result = agent.process_reading(reading)

        assert result["status"] == "Normal"
        assert agent.get_machine_status("M001") == result
        assert agent.get_all_machine_statuses()["M001"] == result

    def test_process_reading_rejects_missing_sensor_values(self):
        agent = AIAgent()
        with pytest.raises(ValueError, match="temperature"):
            agent.process_reading({
                "machine_id": "M001",
                "vibration": {"rms": 0.5},
                "current": 2.5,
            })

    def test_cached_status_is_isolated_from_caller_mutation(self):
        agent = AIAgent()
        result = agent.process_reading({
            "machine_id": "M001",
            "vibration": {"rms": 0.5},
            "temperature": 50.0,
            "current": 2.5,
        })
        result["detected_issues"].append("caller mutation")

        cached = agent.get_machine_status("M001")
        assert "caller mutation" not in cached["detected_issues"]
