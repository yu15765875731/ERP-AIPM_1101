"""Unified CLI Arguments Configuration for Project 2: E-commerce Operations Agent Benchmark Suite."""
from __future__ import annotations

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Project 2: E-commerce Operations Agent - Metric, Dual-Bridge & Guardrail Benchmark Suite"
    )
    parser.add_argument(
        "--mode",
        choices=["offline_verify", "export_blind"],
        default="offline_verify",
        help="Execution mode: run full offline benchmark suite or export label-free blind JSONL inputs.",
    )
    parser.add_argument(
        "--planner_model",
        default="fixed-dashboard-template",
        help="Planner model identifier (e.g., Qwen/Qwen3-8B).",
    )
    parser.add_argument(
        "--explainer_model",
        default="fixed-dashboard-template",
        help="Explainer model identifier (e.g., Qwen/Qwen3-32B).",
    )
    parser.add_argument(
        "--dataset_dir",
        type=Path,
        default=PROJECT_ROOT / "dataset",
        help="Directory for SIM-01 snapshot, structured cases, 30 seed cases, and JSON schemas.",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=PROJECT_ROOT / "results",
        help="Directory to write JSON/CSV benchmark results and Markdown summary reports.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20261125,
        help="Random seed for 200-run multi-shop/SKU exact rational dual-bridge conservation checks.",
    )
    parser.add_argument(
        "--num_property_runs",
        type=int,
        default=200,
        help="Number of random property-based conservation trials.",
    )
    return parser.parse_args()
