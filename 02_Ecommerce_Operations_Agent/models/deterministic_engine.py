"""Project 2: E-commerce Operations Agent - Deterministic Metric, Exact Rational Dual-Bridge & 7-Layer Guardrail Engine.

Implements all core contracts from `项目二PRD_V1.0.md`:
- R-SCOPE: Honest scope validation & anti-silent-clipping on company-wide queries.
- R-DIFF-PERM: Anti-differential-inference lock (blocks CM1/GROSS_MARGIN when `has_cost_perm=False`).
- R-WATERMARK: Cross-table bill watermark alignment gate (orders vs T+1 ad/platform bills).
- R-TIER & R-ALLOC: 3-tier metric availability (`TIER_1_SALES_ONLY` / `TIER_2_SHOP_CM1` / `TIER_3_FULL_SKU_CM1`),
  blocking unallocated shop-level ad fees from distorting SKU-level CM1.
- R-DUAL-BRIDGE: Exact `fractions.Fraction` dual bridge (`primary_component_bridge` vs `counterfactual_reference`)
  with explicit `rounding_residual` closure.
- L1-L7 Guardrail Validator: Blocks fabricated refs, -8000/-6000 bridge mixing, causal savings overclaims & stale revisions.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from fractions import Fraction
import hashlib
from typing import Any

BASELINE_SIM01_ROWS: list[list[Any]] = [
    ["P0", "A", "A1", "40000", "24000", "2000", "8000", "2000"],
    ["P0", "A", "A2", "10000", "6000",  "500",  "2000", "500"],
    ["P0", "B", "B1", "30000", "18000", "1500", "6000", "1500"],
    ["P0", "B", "B2", "20000", "12000", "1000", "4000", "1000"],
    ["P1", "A", "A1", "60000", "36000", "3000", "20000", "3000"],
    ["P1", "A", "A2", "10000", "6000",  "500",  "2000", "500"],
    ["P1", "B", "B1", "30000", "18000", "1500", "6000", "1500"],
    ["P1", "B", "B2", "20000", "12000", "1000", "4000", "1000"],
]
FIELDS = ["net_sales", "cogs", "platform_fee", "ad_fee", "fulfillment_fee"]


def query_metrics(
    rows: list[list[Any]],
    period: str,
    shops: list[str],
    allowed_shops: list[str],
    metric: str = "CM1",
    dimension: str = "TOTAL",
    has_cost_perm: bool = True,
    comparable: bool = True,
    watermarks: dict[str, int] | None = None,
    ad_grain: str = "SKU",
    requested_company_wide: bool = False,
    mutant: str | None = None,
) -> dict[str, Any]:
    if not set(shops) <= set(allowed_shops):
        raise ValueError("FORBIDDEN_SHOP_SCOPE")
    if requested_company_wide and set(allowed_shops) != {"A", "B"} and mutant != "silent_clip_scope":
        raise ValueError("FORBIDDEN_COMPANY_WIDE_CLAIM")
    if metric in ("CM1", "GROSS_MARGIN", "COST_COMPONENTS") and not has_cost_perm and mutant != "allow_diff_cost_leak":
        raise ValueError("FORBIDDEN_COST_METRIC")
    if not comparable:
        raise ValueError("INCOMPARABLE_PERIOD")
    if watermarks and mutant != "ignore_watermark_drift":
        vals = list(watermarks.values())
        if max(vals) - min(vals) > 3600:
            raise ValueError("WATERMARK_DRIFT")
    if metric == "CM1" and dimension == "SKU" and ad_grain == "SHOP_ONLY" and mutant != "naive_ad_allocation":
        raise ValueError("UNALLOCATED_SHOP_AD_FEE_FOR_SKU_CM1")

    selected = [r for r in rows if r[0] == period and r[1] in shops]
    if not selected:
        raise ValueError("NO_DATA")
    keys = [(r[0], r[1], r[2]) for r in selected]
    if len(keys) != len(set(keys)):
        raise ValueError("DUPLICATE_GRAIN")

    if metric == "NET_SALES":
        if any(r[3] is None for r in selected):
            raise ValueError("MISSING_SALES")
        return {"net_sales": sum(Decimal(str(r[3])) for r in selected), "tier": "TIER_1_SALES_ONLY"}

    if any(v is None for r in selected for v in r[3:]):
        if mutant == "fill_null_cost_with_zero":
            selected = [[r[0], r[1], r[2]] + ["0" if v is None else v for v in r[3:]] for r in selected]
        else:
            raise ValueError("MISSING_COST_OR_FEE")

    totals = {f: sum(Decimal(str(r[i + 3])) for r in selected) for i, f in enumerate(FIELDS)}
    totals["gross_margin_after_fulfill"] = (
        totals["net_sales"] - totals["cogs"] - totals["platform_fee"] - totals["fulfillment_fee"]
    )
    totals["cm1"] = totals["net_sales"] - sum(totals[f] for f in FIELDS[1:])
    totals["cm1_rate"] = (totals["cm1"] / totals["net_sales"]) if totals["net_sales"] != 0 else None
    totals["ad_rate"] = (totals["ad_fee"] / totals["net_sales"]) if totals["net_sales"] != 0 else None
    totals["tier"] = "TIER_3_FULL_SKU_CM1" if ad_grain == "SKU" else "TIER_2_SHOP_CM1"
    return totals


def decompose_bridge(p0: dict[str, Any], p1: dict[str, Any], mutant: str | None = None) -> dict[str, Any]:
    component = {
        "delta_net_sales": p1["net_sales"] - p0["net_sales"],
        "delta_cogs_effect": -(p1["cogs"] - p0["cogs"]),
        "delta_platform_effect": -(p1["platform_fee"] - p0["platform_fee"]),
        "delta_ad_effect": -(p1["ad_fee"] - p0["ad_fee"]),
        "delta_fulfillment_effect": -(p1["fulfillment_fee"] - p0["fulfillment_fee"]),
    }
    delta_cm1 = p1["cm1"] - p0["cm1"]
    assert sum(component.values()) == delta_cm1, "Primary component bridge conservation violated"

    counterfactual = None
    if p0["net_sales"] != 0 and p1["net_sales"] != 0:
        m0_exact = Fraction(int(p0["cm1"] * 100), int(p0["net_sales"] * 100))
        m1_exact = Fraction(int(p1["cm1"] * 100), int(p1["net_sales"] * 100))
        r0_exact = Fraction(int(p0["net_sales"] * 100), 100)
        r1_exact = Fraction(int(p1["net_sales"] * 100), 100)
        scale_exact = (r1_exact - r0_exact) * m0_exact
        rate_exact = r1_exact * (m1_exact - m0_exact)
        assert scale_exact + rate_exact == Fraction(int(delta_cm1 * 100), 100), "Exact rational bridge violated"
        q2 = lambda f: (Decimal(f.numerator) / Decimal(f.denominator)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        expected_at_old_margin = q2(r1_exact * m0_exact)
        scale_effect = q2(scale_exact)
        rate_shift_gap = q2(rate_exact)
        rounding_residual = delta_cm1 - (scale_effect + rate_shift_gap)
        counterfactual = {
            "expected_cm1_at_p0_rate": expected_at_old_margin,
            "rate_shift_gap": rate_shift_gap,
            "scale_effect": scale_effect,
            "rounding_residual": rounding_residual,
            "rate_delta_pct_pts": q2((m1_exact - m0_exact) * 100),
        }
        if mutant == "mix_counterfactual_into_delta":
            delta_cm1 = rate_shift_gap

    return {
        "delta_cm1": delta_cm1,
        "primary_component_bridge": component,
        "counterfactual_reference": counterfactual,
    }


def render_deterministic_ops_template(bridge: dict[str, Any], scope_label: str = "A+B") -> str:
    d_cm1 = bridge["delta_cm1"]
    comp = bridge["primary_component_bridge"]
    cf = bridge.get("counterfactual_reference") or {}
    pct_pts = cf.get("rate_delta_pct_pts", "N/A")
    return (
        f"【标准确定性复盘模板｜范围:{scope_label}】本期总经营贡献CM1较上期变动 {d_cm1} 元（贡献率变动 {pct_pts} pct_pts）。"
        f"五项分项桥：净销 {comp['delta_net_sales']}、成本 {comp['delta_cogs_effect']}、平台 {comp['delta_platform_effect']}、"
        f"投放 {comp['delta_ad_effect']}、履约 {comp['delta_fulfillment_effect']}。"
        f"限制说明：仅覆盖CM1_v1已核实科目，统计分解不代表经营因果证明。[SIM-BRIDGE]"
    )


def validate_explanation_guardrail(
    draft: dict[str, Any],
    truth_bridge: dict[str, Any],
    valid_refs: set[str],
    current_rev: int,
    mutant: str | None = None,
) -> dict[str, Any]:
    if draft.get("expected_revision") != current_rev and mutant != "ignore_cas_revision":
        return {"status": "STALE", "layer": "L7_REVISION", "final_text": None}
    if draft.get("external_execution") != "NOT_AVAILABLE":
        return {"status": "BLOCKED", "layer": "L2_EXTERNAL_EXEC_FORBIDDEN", "final_text": None}

    claims = draft.get("claims", [])
    if not claims:
        return {
            "status": "DEGRADED_TEMPLATE",
            "layer": "L5_EMPTY_CLAIMS",
            "final_text": render_deterministic_ops_template(truth_bridge),
        }

    for c in claims:
        if not c.get("refs") or any(r not in valid_refs for r in c["refs"]):
            return {
                "status": "DEGRADED_TEMPLATE",
                "layer": "L3_INVALID_CITATION",
                "final_text": render_deterministic_ops_template(truth_bridge),
            }
        txt = c.get("text", "")
        if c.get("kind") == "FACT" and any(
            bad in txt for bad in ("必定增利", "已节省8000", "砍掉广告立赚", "稳赚回8000", "广告完全无效")
        ):
            return {
                "status": "DEGRADED_TEMPLATE",
                "layer": "L6_CAUSAL_OR_SAVINGS_OVERCLAIM",
                "final_text": render_deterministic_ops_template(truth_bridge),
            }

    if Decimal(str(draft.get("reported_delta_cm1"))) != truth_bridge["delta_cm1"]:
        return {
            "status": "DEGRADED_TEMPLATE",
            "layer": "L5_NUMERIC_MISMATCH",
            "final_text": render_deterministic_ops_template(truth_bridge),
        }
    if not draft.get("covers_limitations", False):
        return {
            "status": "DEGRADED_TEMPLATE",
            "layer": "L5_MISSING_REQUIRED_LIMITATION",
            "final_text": render_deterministic_ops_template(truth_bridge),
        }

    return {"status": "READY", "layer": "PASS", "final_text": " ".join(c["text"] for c in claims)}


def sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
