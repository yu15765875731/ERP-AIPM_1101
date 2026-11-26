"""Model Architecture Skeleton & Pluggable LLM/RAG Adapter for Project 1.

Defines standardized interfaces for:
1. Deterministic Baseline (Route B: Structured Form + Rule Template)
2. Candidate LLMs (Qwen3-8B / Qwen3-32B / DeepSeek-V3.2 via vLLM / OpenAI-compatible API)
3. On-Demand Hybrid Retriever (Exact SQL -> BM25 + pgvector Dense -> RRF -> Optional Qwen3-Reranker-0.6B)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


CANDIDATE_MODEL_REGISTRY: dict[str, dict[str, Any]] = {
    "deterministic-template": {
        "family": "RuleBaseline",
        "role": "Route B zero-LLM deterministic baseline & L1-L7 fallback",
        "context_window": None,
        "deployment": "In-process Python/Java engine",
    },
    "Qwen/Qwen3-8B": {
        "family": "Qwen3",
        "role": "Primary lightweight candidate for T-INTENT / T-EXTRACT / T-EXPLAIN",
        "context_window": 32768,
        "deployment": "vLLM OpenAI-compatible server (recommended) or authorized cloud API",
    },
    "Qwen/Qwen3-32B": {
        "family": "Qwen3",
        "role": "Large-capacity same-family ablation candidate for multi-turn self-correction",
        "context_window": 32768,
        "deployment": "vLLM OpenAI-compatible server (>=16k context enforced)",
    },
    "deepseek-ai/DeepSeek-V3.2": {
        "family": "DeepSeek",
        "role": "Cross-family benchmark candidate (requires enterprise no-training agreement)",
        "context_window": 65536,
        "deployment": "Authorized enterprise endpoint",
    },
}


@dataclass
class ModelCallBudget:
    """Enforces I07 hybrid DAG budget: <=2 calls per explicit node, <=4 calls per free-chat turn."""
    max_calls_per_node: int = 2
    max_calls_per_turn: int = 4
    timeout_seconds: float = 30.0


class RiskAssistantModelBackend(Protocol):
    """Unified protocol for pluggable LLM adapters."""

    def route_intent(self, query: str, task_context: dict[str, Any]) -> dict[str, Any]: ...

    def extract_commitment(self, raw_messages: list[str], anchor_sent_at: str | None) -> dict[str, Any]: ...

    def explain_risk(self, rule_result: dict[str, Any], authorized_evidence: dict[str, Any]) -> str: ...


class OfflineControlledAdapter:
    """Default offline stub adapter used for deterministic contract & guardrail verification."""

    def __init__(self, model_name: str = "deterministic-template", budget: ModelCallBudget | None = None) -> None:
        self.model_name = model_name
        self.budget = budget or ModelCallBudget()

    def describe(self) -> dict[str, Any]:
        return {
            "selected_model": self.model_name,
            "spec": CANDIDATE_MODEL_REGISTRY.get(self.model_name, {"family": "Custom"}),
            "budget": {
                "max_calls_per_node": self.budget.max_calls_per_node,
                "max_calls_per_turn": self.budget.max_calls_per_turn,
                "timeout_seconds": self.budget.timeout_seconds,
            },
        }
