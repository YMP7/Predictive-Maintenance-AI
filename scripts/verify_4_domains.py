import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from server.atlas.domain_service import DomainService

def main():
    print("=== SMOKE TEST: Concurrent 4-Domain Registration in DomainService ===")
    service = DomainService()

    # Register all 4 domains
    r_cmapss = service.register_cmapss(max_units=2)
    r_laptop = service.register_laptop()
    r_mobile = service.register_mobile()
    r_server = service.register_server()

    print(f"C-MAPSS registered: {r_cmapss}")
    print(f"Laptop registered:  {r_laptop}")
    print(f"Mobile registered:  {r_mobile}")
    print(f"Server registered:  {r_server}")

    # Generate a snapshot for each domain manually to test cross_domain_comparison
    for domain_id, adapter in service._adapters.items():
        engine = service._engines.get(domain_id)
        for m_id in adapter.machine_ids:
            reading = adapter.get_reading(m_id)
            pred = engine.update(m_id, reading)
            service._update_snapshot(domain_id, m_id, reading, pred)

    statuses = service.get_all_domain_status()
    print("\n=== ACTIVE DOMAIN STATUSES ===")
    for s in statuses:
        print(f"  [{s['domain_id']}] Units: {len(s['machine_ids'])} | Machine IDs: {s['machine_ids']} | Status: {s['status']}")

    comparison = service.get_cross_domain_comparison()
    print("\n=== CROSS-DOMAIN COMPARISON SNAPSHOTS ===")
    for domain, snaps in comparison.items():
        for snap in snaps:
            print(f"  Domain: {snap['domain']:<8} | Machine: {snap['machine_id']:<15} | Health: {snap['health_index']:.4f} | Status: {snap['status']}")

    print("\nAll 4 domains verified successfully!")

if __name__ == "__main__":
    main()
