"""A machine added to config/machines.json without a simulator is a real MQTT device:
the simulation pass must skip it and keep simulating the others."""
from types import SimpleNamespace

from server.data_service import DataService
from server.sensor_simulator import MultiMachineSimulator


def test_simulation_skips_machines_without_simulator():
    ingested = []
    fake = SimpleNamespace(
        # M005 sits between simulated machines, so a crash on it would also starve M002.
        machine_info={"M001": {}, "M005": {}, "M002": {}},
        simulator=MultiMachineSimulator(),
        ingest_telemetry=lambda mid, reading, source: ingested.append((mid, source)),
    )
    DataService._simulate_once(fake)
    assert ingested == [("M001", "simulation"), ("M002", "simulation")]
