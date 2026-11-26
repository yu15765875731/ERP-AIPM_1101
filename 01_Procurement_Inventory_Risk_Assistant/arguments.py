"""Unified CLI Arguments Configuration for Project 1 Benchmark Suite."""
from __future__ import annotations

import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Project 1: Procurement Inventory Risk Assistant - Benchmark & Guardrail Suite"
    )
    parser.add_argument(
        "--mode",
        choices=["offline_verify", "eval_predictions", "export_blind"],
        default="offline_verify",
        help="Execution mode: offline deterministic+guardrail verification, external prediction scoring, or blind input export.",
    )
    parser.add_argument(
        "--model_name",
        default="deterministic-template",
        help="Target model identifier from CANDIDATE_MODEL_REGISTRY (e.g., Qwen/Qwen3-8B).",
    )
    parser.add_argument(
        "--dataset_dir",
        type=Path,
        default=PROJECT_ROOT / "dataset",
        help="Directory storing structured_cases_v2_1.json, seed_eval_30.json, and tuning_fewshot_dev.json.",
    )
    parser.add_argument(
        "--output_dir",
        type=Path,
        default=PROJECT_ROOT / "results",
        help="Directory to save JSON/CSV evaluation outputs and Markdown reports.",
    )
    parser.add_argument(
        "--predictions",
        type=Path,
        default=None,
        help="Optional JSONL file of external model/API outputs for blind scoring.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=20261125,
        help="Random seed for 300-run property-based inventory conservation checks.",
    )
    parser.add_argument(
        "--num_property_runs",
        type=int,
        default=300,
        help="Number of random multi-batch conservation trials.",
    )
    return parser.parse_args()
