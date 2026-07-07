import time
import psutil
from server.ai_agent import AIAgent
from server.sensor_simulator import MultiMachineSimulator

def test_processing_latency():
    print("Testing processing latency...")
    agent = AIAgent()
    simulator = MultiMachineSimulator()
    
    latencies = []
    
    for _ in range(100):
        reading = simulator.get_machine_reading("M001")
        
        start = time.time()
        _ = agent.process_reading(reading)
        latency = (time.time() - start) * 1000  # Convert to ms
        
        latencies.append(latency)
    
    avg_latency = sum(latencies) / len(latencies)
    max_latency = max(latencies)
    
    print(f"Average latency: {avg_latency:.2f}ms")
    print(f"Max latency: {max_latency:.2f}ms")
    
    assert avg_latency < 100, f"Average latency {avg_latency}ms exceeds 100ms"
    assert max_latency < 500, f"Max latency {max_latency}ms exceeds 500ms"

def test_memory_usage():
    print("Testing memory footprint...")
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB
    
    simulator = MultiMachineSimulator()
    agent = AIAgent()
    
    for _ in range(1000):
        readings = simulator.get_all_readings()
        for reading in readings:
            agent.process_reading(reading)
            
    final_memory = process.memory_info().rss / 1024 / 1024  # MB
    memory_growth = final_memory - initial_memory
    
    print(f"Memory growth: {memory_growth:.2f}MB")
    assert memory_growth < 100, f"Memory growth {memory_growth}MB exceeds 100MB"

if __name__ == "__main__":
    test_processing_latency()
    test_memory_usage()
    print("All performance tests passed successfully!")
