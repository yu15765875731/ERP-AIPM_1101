"""Master Benchmark Runner for ERP-AIPM Dual-Project Suite.

Sequentially executes:
1. 01_Procurement_Inventory_Risk_Assistant/experiments.py
2. 02_Ecommerce_Operations_Agent/experiments.py
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SUITES = [
    ROOT / "01_Procurement_Inventory_Risk_Assistant" / "experiments.py",
    ROOT / "02_Ecommerce_Operations_Agent" / "experiments.py",
]

def main() -> int:
    for script in SUITES:
        print(f"=== Running {script.parent.name} ===")
        rc = subprocess.call([sys.executable, str(script)])
        if rc != 0:
            return rc
    print("=== All ERP-AIPM benchmark suites passed! ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
