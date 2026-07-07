"""
Demonstration Scenarios for AI Digital Twin Prototype
"""

from server.sensor_simulator import MultiMachineSimulator
from server.ai_agent import AIAgent
from server.data_service import get_data_service
import time
import json

class DemoScenario:
    """Base demo scenario"""
    
    def __init__(self, name: str, duration: int = 60):
        self.name = name
        self.duration = duration
        self.simulator = MultiMachineSimulator()
        self.agent = AIAgent()
        self.service = get_data_service()
    
    def run(self):
        """Run demonstration"""
        print(f"\n{'='*60}")
        print(f"DEMO: {self.name}")
        print(f"{'='*60}\n")
        
        self.service.start_simulation(interval=1)
        
        start_time = time.time()
        iteration = 0
        
        while time.time() - start_time < self.duration:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")
            
            # Get summary
            summary = self.service.get_dashboard_summary()
            
            # Print status
            print(f"Total Machines: {summary['total_machines']}")
            print(f"Status Distribution:")
            print(f"  Normal: {summary['machine_status_counts']['Normal']}")
            print(f"  Warning: {summary['machine_status_counts']['Warning']}")
            print(f"  Critical: {summary['machine_status_counts']['Critical']}")
            
            # Print alerts
            recent_alerts = self.service.get_recent_alerts(limit=3)
            if recent_alerts:
                print(f"\nRecent Alerts ({len(recent_alerts)}):")
                for alert in recent_alerts[-3:]:
                    print(f"  [{alert['severity']}] {alert['message']}")
            
            time.sleep(5)
        
        self.service.stop_simulation()
        print(f"\n{'='*60}")
        print(f"DEMO COMPLETED: {self.name}")
        print(f"{'='*60}\n")

class NormalOperationDemo(DemoScenario):
    """Demonstrate normal operation"""
    
    def __init__(self):
        super().__init__("Normal Operation", duration=30)

class FaultDetectionDemo(DemoScenario):
    """Demonstrate fault detection"""
    
    def __init__(self):
        super().__init__("Fault Detection", duration=60)
    
    def run(self):
        """Run fault detection demo"""
        print(f"\n{'='*60}")
        print(f"DEMO: {self.name}")
        print(f"{'='*60}\n")
        
        # Inject faults into both scenario simulator and service simulator to ensure background thread reads it
        self.simulator.machines["M002"].fault_mode = "bearing_wear"
        self.simulator.machines["M003"].fault_mode = "misalignment"
        self.service.simulator.machines["M002"].fault_mode = "bearing_wear"
        self.service.simulator.machines["M003"].fault_mode = "misalignment"
        
        self.service.start_simulation(interval=1)
        
        start_time = time.time()
        iteration = 0
        
        while time.time() - start_time < self.duration:
            iteration += 1
            print(f"\n--- Iteration {iteration} ---")
            
            summary = self.service.get_dashboard_summary()
            
            print(f"Status Distribution:")
            print(f"  Normal: {summary['machine_status_counts']['Normal']}")
            print(f"  Warning: {summary['machine_status_counts']['Warning']}")
            print(f"  Critical: {summary['machine_status_counts']['Critical']}")
            
            # Show machine details
            for machine in summary['machines']:
                if machine['status'] != 'Normal':
                    print(f"\n{machine['machine_info']['name']} ({machine['machine_id']}):")
                    print(f"  Status: {machine['status']}")
                    print(f"  Fault: {machine['fault_type']}")
                    print(f"  Issues: {', '.join(machine['detected_issues'])}")
                    print(f"  RUL: {machine['rul_days']} days")
            
            time.sleep(5)
        
        self.service.stop_simulation()
        print(f"\n{'='*60}")
        print(f"DEMO COMPLETED: {self.name}")
        print(f"{'='*60}\n")

class RULEstimationDemo(DemoScenario):
    """Demonstrate RUL estimation"""
    
    def __init__(self):
        super().__init__("RUL Estimation", duration=120)
    
    def run(self):
        """Run RUL estimation demo"""
        print(f"\n{'='*60}")
        print(f"DEMO: {self.name}")
        print(f"{'='*60}\n")
        
        # Inject degrading fault into both scenario simulator and service simulator to ensure background thread reads it
        self.simulator.machines["M004"].fault_mode = "overheating"
        self.service.simulator.machines["M004"].fault_mode = "overheating"
        
        self.service.start_simulation(interval=1)
        
        start_time = time.time()
        iteration = 0
        
        while time.time() - start_time < self.duration:
            iteration += 1
            
            if iteration % 10 == 0:  # Print every 10 iterations (since interval=1s, approx every 10s)
                print(f"\n--- Iteration {iteration} ---")
                
                status = self.service.get_machine_status("M004")
                if status:
                    print(f"Machine: {status['machine_info']['name']}")
                    print(f"Status: {status['status']}")
                    print(f"RUL: {status['rul_days']} days")
                    print(f"Confidence: {status['rul_confidence']:.2%}")
                    print(f"Recommendation: {status['recommendation']}")
            
            time.sleep(1)
        
        self.service.stop_simulation()
        print(f"\n{'='*60}")
        print(f"DEMO COMPLETED: {self.name}")
        print(f"{'='*60}\n")

if __name__ == "__main__":
    # Run demonstrations
    print("AI DIGITAL TWIN PROTOTYPE - DEMONSTRATION SUITE")
    print("=" * 60)
    
    # Demo 1: Normal Operation
    demo1 = NormalOperationDemo()
    demo1.run()
    
    # Demo 2: Fault Detection
    demo2 = FaultDetectionDemo()
    demo2.run()
    
    # Demo 3: RUL Estimation
    demo3 = RULEstimationDemo()
    demo3.run()
    
    print("\nAll demonstrations completed!")
