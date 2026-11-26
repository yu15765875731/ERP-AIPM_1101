"""Model Architecture Skeleton & Tiered LLM/Reasoning Adapter for Project 2: E-commerce Operations Agent.

Follows industry best practices validated in competitor research (e.g., FineChatBI & Guandata):
1. Route B Zero-LLM Fixed Review Dashboard & Template Baseline
2. Lightweight General Model (e.g., Qwen3-8B) for fast T-PLAN Text-to-Tool-DSL mapping
3. Reasoning / Large Model (e.g., Qwen3-32B / DeepSeek-V3.2) for grounded T-EXPLAIN synthesis
4. Private Deployment Constraint: Enforce vLLM (>=16k context); disallow Ollama due to System Prompt drop risks
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


OPS_CANDIDATE_MODELS: dict[str, dict[str, Any]] = {
    "fixed-dashboard-template": {
        "tier": "Route_B_Baseline",
        "role": "Zero-LLM weekly review dashboard & L1-L7 deterministic fallback",
        "min_context_tokens": None,
        "private_runtime": "Java/Python Metric Service",
    },
    "Qwen/Qwen3-8B": {
        "tier": "Fast_Planner_Candidate",
        "role": "T-PLAN controlled tool-DSL routing & scope clarification",
        "min_context_tokens": 16384,
        "private_runtime": "vLLM OpenAI-compatible server (Ollama prohibited)",
    },
    "Qwen/Qwen3-32B": {
        "tier": "Deep_Analyzer_Candidate",
        "role": "Multi-step anomaly drill-down planning & T-EXPLAIN FACT/ASSUMPTION synthesis",
        "min_context_tokens": 16384,
        "private_runtime": "vLLM OpenAI-compatible server (Ollama prohibited)",
    },
    "Authorized-Enterprise-LLM": {
        "tier": "Cloud_Benchmark_Candidate",
        "role": "Cross-family benchmark (e.g., DeepSeek-V3.2 / R1 under signed no-training DPA)",
        "min_context_tokens": 32768,
        "private_runtime": "Enterprise VPC endpoint",
    },
}


@dataclass
class OpsAgentTurnBudget:
    """Enforces hybrid DAG budget: <=5 LLM generations, <=6 read-only tool calls, <=30s wall-clock per turn."""
    max_llm_generations: int = 5
    max_tool_calls: int = 6
    max_additional_drilldowns: int = 2
    max_schema_repairs: int = 1
    wall_clock_timeout_sec: float = 30.0


class OpsAgentModelSkeleton:
    """Pluggable adapter skeleton for offline verification and live vLLM benchmarking."""

    def __init__(self, planner_model: str = "fixed-dashboard-template", explainer_model: str = "fixed-dashboard-template") -> None:
        self.planner_model = planner_model
        self.explainer_model = explainer_model
        self.budget = OpsAgentTurnBudget()

    def describe(self) -> dict[str, Any]:
        return {
            "planner_model": self.planner_model,
            "explainer_model": self.explainer_model,
            "planner_spec": OPS_CANDIDATE_MODELS.get(self.planner_model, {"tier": "Custom"}),
            "explainer_spec": OPS_CANDIDATE_MODELS.get(self.explainer_model, {"tier": "Custom"}),
            "turn_budget": {
                "max_llm_generations": self.budget.max_llm_generations,
                "max_tool_calls": self.budget.max_tool_calls,
                "max_additional_drilldowns": self.budget.max_additional_drilldowns,
                "wall_clock_timeout_sec": self.budget.wall_clock_timeout_sec,
            },
        }
