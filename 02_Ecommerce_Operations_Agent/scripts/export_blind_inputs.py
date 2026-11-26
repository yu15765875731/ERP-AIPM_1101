"""Helper script to export label-free JSONL blind inputs for Project 2 external LLM evaluation."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    sys.exit(subprocess.call([sys.executable, str(ROOT / "experiments.py"), "--mode", "export_blind"]))
