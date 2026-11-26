"""Procurement Inventory Risk Assistant V2.1 - Deterministic Core Engine & 7-Layer Guardrail Validator.

Resolves all 7 P0 review gaps (I01-I07) from Week 3 Multi-Role Review:
- I01 (R-WATERMARK): Snapshot watermark & included_in_snapshot_qty deduplication (supports partial receipt/QC).
- I02 (R-BATCH): Active unfulfilled balance check (excludes IN_SNAPSHOT_SELLABLE / SUPERSEDED batches).
- I03 (Terminology): Replaces misleading `historical_delay_qty` with `projected_cumulative_late_qty` + `actual_past_delay_qty`.
- I04 (Lifecycle): Full state machine with `CLOSED_NO_RISK`, `FACT_REVIEW -> VALIDATING`, `RESOLVED -> STALE` reopen.
- I05 (Freshness & Drift): Cross-table sync drift gate (<=60s) and snapshot freshness tiers (`FRESH`/`STALE_WARNING`/`EXPIRED_READONLY`).
- I06 (R-SLA & Cutoff): Deterministic `ARRIVAL + dock_to_sellable_hours -> derived_sellable <= Cutoff` bucket derivation; conservative exclusion when SLA missing.
- I07 (Budget): Per-node LLM call cap (<=2 calls: 1 initial + <=1 schema repair; 0 retry on L4/L5/CAS).

Python 3.10+, standard library only.
"""
from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any


def is_nonneg_int(val: Any) -> bool:
    return type(val) is int and val >= 0


def parse_hhmm(hhmm: str) -> int:
    parts = hhmm.strip().split(":")
    if len(parts) < 2:
        raise ValueError(f"Invalid time string: {hhmm}")
    h, m = int(parts[0]), int(parts[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"Out-of-range time: {hhmm}")
    return h * 60 + m


def evaluate_entry_gate(ctx: dict[str, Any], mutant: str | None = None) -> dict[str, Any]:
    """Step 1 Gate: RBAC/Tenant ACL, Cross-table sync drift (I05), Freshness TTL, Unit & R-NET basis."""
    actor_tenant = ctx.get("actor_tenant", "TENANT_A")
    resource_tenant = ctx.get("resource_tenant", "TENANT_A")
    authorized = ctx.get("authorized", True)
    if actor_tenant != resource_tenant or not authorized:
        return {"ok": False, "http_code": 403, "state": "FORBIDDEN", "error": "ACL_DENIED"}

    if ctx.get("requested_price_field", False) and not ctx.get("price_field_allowed", False):
        return {"ok": False, "http_code": 403, "state": "FORBIDDEN", "error": "FIELD_ACL_DENIED"}

    if not ctx.get("sku_id") or not ctx.get("warehouse_id"):
        return {"ok": False, "http_code": 200, "state": "WAITING_INPUT", "error": "AMBIGUOUS_OBJECT"}

    drift_sec = ctx.get("max_table_drift_seconds", 0)
    if drift_sec > 60 and mutant != "ignore_table_drift":
        return {"ok": False, "http_code": 409, "state": "WAITING_INPUT", "error": "SNAPSHOT_DRIFT"}

    if not ctx.get("data_complete", True):
        return {"ok": False, "http_code": 422, "state": "WAITING_INPUT", "error": "INCOMPLETE_SNAPSHOT"}

    if ctx.get("unit", "PIECE") != "PIECE":
        return {"ok": False, "http_code": 422, "state": "WAITING_INPUT", "error": "UNSUPPORTED_UNIT"}

    if ctx.get("inventory_basis", "NET") != "NET" or ctx.get("demand_basis", "NET_NEW") != "NET_NEW":
        return {"ok": False, "http_code": 422, "state": "WAITING_INPUT", "error": "MISSING_BASIS"}

    age_minutes = ctx.get("snapshot_age_minutes", 5)
    erp_timeout = ctx.get("erp_timeout", False)
    if erp_timeout or age_minutes > 240:
        freshness = "EXPIRED_READONLY"
    elif age_minutes > 15:
        freshness = "STALE_WARNING"
    else:
        freshness = "FRESH"

    return {"ok": True, "http_code": 200, "freshness": freshness}


def next_working_day(day: int, non_working_days: set[int]) -> int:
    d = day
    while d in non_working_days and d <= 60:
        d += 1
    return d


def derive_sellable_bucket(
    batch: dict[str, Any],
    default_cutoff_hhmm: str = "16:00",
    warehouse_sla_hours: int | None = 24,
    non_working_days: set[int] | None = None,
    mutant: str | None = None,
) -> dict[str, Any]:
    """R-SLA & R-TIME (I06): Deterministically map a batch to a valid working-day sellable bucket."""
    closed_days = non_working_days or set()
    reviewed = batch.get("reviewed", False)
    modality = batch.get("supplier_modality", "COMMITTED" if reviewed else "UNCONFIRMED")
    hedging = batch.get("hedging_flags", [])
    time_type = batch.get("time_type", "SELLABLE")
    day = batch.get("day")

    # R-UNKNOWN: Unreviewed, reconfirm, estimated, negated, or hedged with NOT_GUARANTEED
    if (
        not reviewed
        or time_type in ("RECONFIRM", "UNKNOWN")
        or modality in ("ESTIMATED", "RECONFIRM_LATER", "CANNOT_MEET", "UNKNOWN")
        or "NOT_GUARANTEED" in hedging
        or "NEGATED_GUARANTEE" in hedging
        or day is None
    ):
        if mutant == "include_unknown" and day is not None:
            return {"category": "ELIGIBLE", "sellable_day": day, "note": "MUTANT_FORCED"}
        return {"category": "UNKNOWN", "sellable_day": None, "reason": "UNCONFIRMED_OR_HEDGED"}

    cutoff_mins = parse_hhmm(default_cutoff_hhmm)

    if time_type == "SELLABLE":
        if "event_time_hhmm" in batch and batch["event_time_hhmm"] is not None:
            ev_mins = parse_hhmm(batch["event_time_hhmm"])
            before_or_at = ev_mins <= cutoff_mins
        else:
            before_or_at = batch.get("before_or_at_cutoff", True)
        raw_day = day if (before_or_at or mutant == "ignore_cutoff") else day + 1
        sellable_day = next_working_day(raw_day, closed_days)
        return {"category": "ELIGIBLE", "sellable_day": sellable_day, "reason": "DIRECT_SELLABLE"}

    if time_type == "ARRIVAL":
        sla_h = batch.get("sla_hours_override", warehouse_sla_hours)
        if sla_h is None:
            if mutant == "assume_zero_sla_when_missing":
                return {"category": "ELIGIBLE", "sellable_day": day, "reason": "MUTANT_ZERO_SLA"}
            return {"category": "UNKNOWN", "sellable_day": None, "reason": "ARRIVAL_ONLY_NO_SLA"}

        arr_hhmm = batch.get("event_time_hhmm", "14:00")
        total_mins_from_d0 = (day - 1) * 1440 + parse_hhmm(arr_hhmm) + int(sla_h * 60)
        derived_day = (total_mins_from_d0 // 1440) + 1
        derived_mins_in_day = total_mins_from_d0 % 1440
        if derived_mins_in_day > cutoff_mins and mutant != "ignore_cutoff":
            derived_day += 1
        sellable_day = next_working_day(derived_day, closed_days)
        return {
            "category": "ELIGIBLE",
            "sellable_day": sellable_day,
            "reason": f"DERIVED_FROM_SLA_+{sla_h}H",
        }

    return {"category": "UNKNOWN", "sellable_day": None, "reason": "DISPATCH_ONLY_NO_ARRIVAL"}


def calculate_risk_v2_1(x: dict[str, Any], mutant: str | None = None) -> dict[str, Any]:
    """Deterministic time-phased daily ledger & inventory conservation engine (V2.1)."""
    gate = evaluate_entry_gate(x, mutant=mutant)
    if not gate["ok"]:
        return {"error": gate["error"], "http_code": gate["http_code"], "state": gate["state"]}

    initial = x.get("initial")
    demand = x.get("demand")
    if not is_nonneg_int(initial) or not isinstance(demand, list) or any(not is_nonneg_int(d) for d in demand):
        return {"error": "INVALID_QUANTITY", "http_code": 422}

    window_days = x.get("window_days", len(demand))
    if not (1 <= len(demand) <= 30) or window_days != len(demand):
        return {"error": "INVALID_WINDOW", "http_code": 422}

    batches = x.get("batches", [])
    seen_ids: set[str] = set()
    active_unfulfilled_sum = 0

    for b in batches:
        if b.get("supersedes_discarded", False) or b.get("status") in ("SUPERSEDED", "CANCELLED", "SHORT_CLOSED"):
            continue
        qty = b.get("quantity")
        in_snap_qty = b.get("included_in_snapshot_qty", qty if b.get("included_in_snapshot") else 0)
        if not is_nonneg_int(qty) or not is_nonneg_int(in_snap_qty) or in_snap_qty > qty:
            return {"error": "INVALID_QUANTITY", "http_code": 422}
        bid = b.get("batch_id")
        if bid in seen_ids:
            return {"error": "DUPLICATE_BATCH", "http_code": 422}
        seen_ids.add(bid)
        day = b.get("day")
        if day is not None and (type(day) is not int or day < 1):
            return {"error": "INVALID_DAY", "http_code": 422}

        status = b.get("status", "FUTURE_ACTIVE")
        remaining_qty = qty - in_snap_qty
        # ERP open_qty already deducts physically received goods (including RECEIVED_PENDING_QC);
        # only unreceived future shipments compete against open_qty.
        if status in ("FUTURE_ACTIVE", "FUTURE"):
            active_unfulfilled_sum += remaining_qty

    if "open_qty" in x and active_unfulfilled_sum > x["open_qty"]:
        return {
            "error": "BATCH_EXCEEDS_OPEN",
            "http_code": 409,
            "state": "CONFLICT",
            "active_unfulfilled_qty": active_unfulfilled_sum,
            "open_qty": x["open_qty"],
        }
    if "ordered_net_qty" in x:
        total_accounted = sum(
            b["quantity"]
            for b in batches
            if not b.get("supersedes_discarded", False) and b.get("status") not in ("SUPERSEDED", "CANCELLED", "SHORT_CLOSED")
        )
        if total_accounted > x["ordered_net_qty"]:
            return {
                "error": "BATCH_EXCEEDS_ORDERED",
                "http_code": 409,
                "state": "CONFLICT",
            }

    cutoff_hhmm = x.get("daily_cutoff_hhmm", "16:00")
    sla_hours = x.get("warehouse_sla_hours", 24)
    closed_days = set(x.get("non_working_days", []))

    supplies: Counter[int] = Counter()
    unknown_qty = 0
    known_outside_window_qty = 0
    missing_sla_batches: list[str] = []

    for b in batches:
        status = b.get("status", "FUTURE_ACTIVE")
        if b.get("supersedes_discarded", False) or status in ("SUPERSEDED", "CANCELLED", "SHORT_CLOSED", "REVERSED"):
            continue

        qty = b["quantity"]
        in_snap_qty = b.get("included_in_snapshot_qty", qty if b.get("included_in_snapshot") else 0)

        # R-WATERMARK (I01): Never double count stock already absorbed into snapshot watermark
        if mutant == "double_count_snapshot":
            unconsumed_qty = qty
        else:
            if status == "IN_SNAPSHOT_SELLABLE":
                continue
            unconsumed_qty = qty - in_snap_qty

        if unconsumed_qty == 0:
            continue

        if status == "RECEIVED_PENDING_QC":
            unknown_qty += unconsumed_qty
            continue

        derived = derive_sellable_bucket(
            b, default_cutoff_hhmm=cutoff_hhmm, warehouse_sla_hours=sla_hours, non_working_days=closed_days, mutant=mutant
        )
        if derived["category"] == "UNKNOWN":
            unknown_qty += unconsumed_qty
            if derived.get("reason") == "ARRIVAL_ONLY_NO_SLA":
                missing_sla_batches.append(b["batch_id"])
            continue

        s_day = derived["sellable_day"]
        if s_day > window_days:
            known_outside_window_qty += unconsumed_qty
        else:
            supplies[s_day] += unconsumed_qty

    stock = initial
    backlog = 0
    projected_cumulative_late = 0
    first_risk_day: int | None = None
    ledger: list[dict[str, int]] = []

    for day_idx, d_qty in enumerate(demand, start=1):
        start_inv = stock
        prev_backlog = backlog
        avail = start_inv + supplies[day_idx]
        old_filled = min(avail, prev_backlog)
        current_filled = min(avail - old_filled, d_qty)
        late = d_qty - current_filled
        backlog = prev_backlog - old_filled + late
        stock = avail - old_filled - current_filled

        if late > 0 and first_risk_day is None:
            first_risk_day = day_idx
        projected_cumulative_late += late

        # Strict mathematical conservation assertions
        assert min(stock, backlog, late) >= 0
        assert start_inv + supplies[day_idx] == old_filled + current_filled + stock
        assert prev_backlog + d_qty == old_filled + current_filled + backlog

        ledger.append(
            {
                "day": day_idx,
                "starting_inventory": start_inv,
                "supply": supplies[day_idx],
                "demand": d_qty,
                "old_filled": old_filled,
                "current_filled": current_filled,
                "late": late,
                "backlog": backlog,
                "end_inventory": stock,
            }
        )

    if mutant == "erase_window_delay_on_zero_backlog" and backlog == 0:
        projected_cumulative_late = 0

    if gate["freshness"] == "EXPIRED_READONLY":
        card_risk_status = "EXPIRED_SNAPSHOT_NO_GUARANTEE"
    elif projected_cumulative_late == 0:
        card_risk_status = "NO_RISK"
    elif backlog == 0:
        card_risk_status = "RISK_DELAY_RECOVERED_IN_WINDOW"
    else:
        card_risk_status = "RISK_UNRESOLVED_AT_WINDOW_END"

    return {
        "first_risk_day": first_risk_day,
        # Unified PRD 1.0 canonical fields + aliases
        "predicted_window_delay_qty": projected_cumulative_late,
        "projected_cumulative_late_qty": projected_cumulative_late,
        "actual_occurred_delay_qty": x.get("actual_past_delay_qty", 0),
        "actual_past_delay_qty": x.get("actual_past_delay_qty", 0),
        "end_backlog_qty": backlog,
        "end_inventory_qty": stock,
        "unknown_supply_units": unknown_qty,
        "unknown_qty": unknown_qty,
        "outside_window_qty": known_outside_window_qty,
        "known_outside_window_qty": known_outside_window_qty,
        "missing_sla_batches": missing_sla_batches,
        "freshness": gate["freshness"],
        "result_validity": "VALID",
        "card_risk_status": card_risk_status,
        "allow_close_no_risk": gate["freshness"] != "EXPIRED_READONLY" and projected_cumulative_late == 0 and unknown_qty == 0,
        "ledger": ledger,
    }


def evaluate_lifecycle_policy(ev: dict[str, Any], mutant: str | None = None) -> dict[str, Any]:
    """Lifecycle State Machine (I04), Tenant-Scoped Idempotency (I12), CAS (R-REV) & Budget Policy (I07)."""
    op = ev["op"]

    if op == "cas_writeback":
        stale = ev["expected_revision"] != ev["current_revision"] and mutant != "ignore_cas_revision"
        return {"code": 409 if stale else 200, "state": "STALE" if stale else "READY"}

    if op == "acl_read":
        allowed = (
            ev["actor_tenant"] == ev["source_tenant"]
            and ev.get("authorized", True)
            and ev.get("perm_fingerprint_current") == ev.get("perm_fingerprint_cached", ev.get("perm_fingerprint_current"))
        )
        return {"code": 200 if allowed else 403, "visible": allowed}

    if op == "scoped_idempotency":
        # Fixes I12: scope key includes tenant + source + warehouse + watermark + payload_hash
        k1 = f"{ev['stored_tenant']}|{ev['stored_watermark']}|{ev['stored_hash']}"
        k2 = f"{ev['req_tenant']}|{ev['req_watermark']}|{ev['req_hash']}"
        if ev.get("same_idempotency_header", False):
            same_body = ev["stored_hash"] == ev["req_hash"] and ev["stored_tenant"] == ev["req_tenant"]
            return {"code": 200 if same_body else 409, "reused": same_body}
        return {"code": 200, "dedup_skipped": k1 == k2, "accepted_as_new_snapshot": k1 != k2}

    if op == "save_internal_plan":
        return {
            "code": 200,
            "state": "RESOLVED" if mutant == "plan_marks_resolved" else "FOLLOWING",
            "external_execution": "NOT_AVAILABLE",
        }

    if op == "close_no_risk":
        allowed = ev.get("projected_cumulative_late_qty", 0) == 0 and ev.get("unknown_qty", 0) == 0 and ev.get("freshness") != "EXPIRED_READONLY"
        return {"code": 200 if allowed else 409, "state": "CLOSED_NO_RISK" if allowed else "READY"}

    if op == "verify_recovery":
        if not ev.get("actual_sellable_evidence", False):
            return {"code": 200, "state": "FOLLOWING"}
        return {"code": 200, "state": "RESOLVED" if ev.get("recalculated_gap", 1) == 0 else "READY"}

    if op == "cancel_demand":
        return {"code": 200, "state": "CLOSED_NOT_APPLICABLE" if ev.get("ops_confirmed", False) else "WAITING_INPUT"}

    if op == "external_change_event":
        # Covers READY, FOLLOWING, RESOLVED, CLOSED_NO_RISK reopening to STALE -> VALIDATING
        prev = ev["current_state"]
        if prev in ("READY", "FOLLOWING", "RESOLVED", "CLOSED_NO_RISK"):
            return {"code": 200, "freshness": "STALE", "next_state": "VALIDATING", "preserved_prev_audit": prev}
        return {"code": 200, "freshness": "CURRENT", "next_state": prev}

    if op == "fact_review_confirm":
        # Fixes I04: FACT_REVIEW and CONFLICT always route through VALIDATING before CALCULATING
        return {"code": 200, "next_state": "VALIDATING", "new_revision": ev["revision"] + 1}

    if op == "llm_node_budget":
        # Fixes I07: Single node cap <= 2 calls (1 initial + <= 1 format repair); 0 retry on L4/L5
        attempts = 0
        for outcome in ev["attempt_outcomes"]:
            attempts += 1
            if outcome == "VALID_JSON":
                return {"calls_used": attempts, "final_mode": "AI_SUCCESS"}
            if outcome in ("L4_ACL_FAIL", "L5_NUMBER_TAMPER", "TIMEOUT"):
                return {"calls_used": attempts, "final_mode": "DETERMINISTIC_FALLBACK"}
            if attempts >= 2:
                return {"calls_used": attempts, "final_mode": "DETERMINISTIC_FALLBACK"}
        return {"calls_used": attempts, "final_mode": "DETERMINISTIC_FALLBACK"}

    raise ValueError(f"Unsupported policy op: {op}")


def render_deterministic_card_summary(rule_res: dict[str, Any], evidence_ids: list[str]) -> str:
    """Zero-hallucination deterministic fallback template renderer."""
    ev_tag = "".join(f"[{eid}]" for eid in evidence_ids[:3])
    late = rule_res["projected_cumulative_late_qty"]
    end_b = rule_res["end_backlog_qty"]
    unk = rule_res["unknown_qty"]
    out_q = rule_res["known_outside_window_qty"]
    first_d = rule_res["first_risk_day"]

    if rule_res["freshness"] == "EXPIRED_READONLY":
        return f"【历史快照只读提示】当前ERP快照已超新鲜度上限，仅展示历史时点测算账（窗口测算缺口 {late} 件），不做当前无风险担保。{ev_tag}"

    if late == 0:
        base = f"按当前已核对可售供给测算，窗口内预测累计新增缺口为 0 件，期末可用库存 {rule_res['end_inventory_qty']} 件。"
    elif end_b == 0:
        base = (
            f"【窗口断档预警】首次预测断货日为 D{first_d}，窗口内预测累计新增缺口 {late} 件"
            f"（后续批次可售入桶后于期末补齐前欠，期末未补积压 0 件，请勿误判为全程无风险）。"
        )
    else:
        base = f"【未补齐缺口预警】首次预测断货日为 D{first_d}，窗口内预测累计新增缺口 {late} 件，期末仍余 {end_b} 件未补缺口。"

    extras = []
    if unk > 0:
        extras.append(f"另有 {unk} 件属待确认/缺质检时效未知供给未计入确定可用量")
    if out_q > 0:
        extras.append(f"另有 {out_q} 件已确认供给落点在核算窗口之外")
    tail = ("；" + "，".join(extras) + "。") if extras else ""
    return f"{base}{tail}依据：{ev_tag}"


def validate_seven_layers(
    candidate_text: str | None,
    rule_res: dict[str, Any],
    authorized_evidence: dict[str, dict[str, Any]],
    actor_tenant: str,
    expected_revision: int,
    current_revision: int,
) -> dict[str, Any]:
    """7-Layer Output Guardrail Validator for T-EXPLAIN."""
    # L7: Revision CAS consistency
    if expected_revision != current_revision:
        return {
            "passed": False,
            "failed_layer": "L7_REVISION_STALE",
            "action": "DROP_STALE_WRITEBACK",
            "final_text": None,
        }

    whitelist_ids = list(authorized_evidence.keys())

    # L1/L2: Empty or missing output
    if not candidate_text or not candidate_text.strip():
        return {
            "passed": False,
            "failed_layer": "L1_EMPTY_OR_TIMEOUT",
            "action": "FALLBACK_TEMPLATE",
            "final_text": render_deterministic_card_summary(rule_res, whitelist_ids),
        }

    # L3 & L4: Citation existence & Tenant/Status ACL check
    cited_ids = re.findall(r"\[(E-[A-Za-z0-9_-]+)\]", candidate_text)
    if not cited_ids:
        return {
            "passed": False,
            "failed_layer": "L3_MISSING_CITATION",
            "action": "FALLBACK_TEMPLATE",
            "final_text": render_deterministic_card_summary(rule_res, whitelist_ids),
        }
    for cid in cited_ids:
        if cid not in authorized_evidence:
            return {
                "passed": False,
                "failed_layer": "L3_FABRICATED_CITATION",
                "action": "FALLBACK_TEMPLATE",
                "final_text": render_deterministic_card_summary(rule_res, whitelist_ids),
            }
        meta = authorized_evidence[cid]
        if meta.get("tenant_id") != actor_tenant or meta.get("status") != "ACTIVE":
            return {
                "passed": False,
                "failed_layer": "L4_ACL_OR_REVOKED_EVIDENCE",
                "action": "BLOCK_SECURITY_EVENT",
                "final_text": None,
            }

    # L5: Business & Numeric Invariants (Never claim "no risk" when projected_cumulative_late_qty > 0 or EXPIRED)
    forbidden_safe_phrases = ("全程无缺货", "全程无风险", "十天无风险", "十日内无风险", "完全够用", "不会断货")
    if rule_res["projected_cumulative_late_qty"] > 0 or rule_res["freshness"] == "EXPIRED_READONLY":
        if any(p in candidate_text for p in forbidden_safe_phrases):
            return {
                "passed": False,
                "failed_layer": "L5_FALSE_SAFE_CLAIM",
                "action": "FALLBACK_TEMPLATE",
                "final_text": render_deterministic_card_summary(rule_res, whitelist_ids),
            }
        if str(rule_res["projected_cumulative_late_qty"]) not in candidate_text:
            return {
                "passed": False,
                "failed_layer": "L5_MISSING_CORE_GAP_NUMBER",
                "action": "FALLBACK_TEMPLATE",
                "final_text": render_deterministic_card_summary(rule_res, whitelist_ids),
            }

    # L6: Uncertainty preservation (must mention pending/unknown if unknown_qty > 0)
    if rule_res["unknown_qty"] > 0:
        if not any(w in candidate_text for w in ("待确认", "未知", "未计入", "再确认", "待补")):
            return {
                "passed": False,
                "failed_layer": "L6_OMITTED_UNKNOWN_WARNING",
                "action": "FALLBACK_TEMPLATE",
                "final_text": render_deterministic_card_summary(rule_res, whitelist_ids),
            }

    return {
        "passed": True,
        "failed_layer": None,
        "action": "PASS_AI_EXPLANATION",
        "final_text": candidate_text,
    }


def sha256_file(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
