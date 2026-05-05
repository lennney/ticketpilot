#!/usr/bin/env python
"""Phase 10.3 — P0 Layered Trace Export.

Runs the pipeline for P0-related wrong cases and exports full per-ranker
trace data (keyword, vector, fused, final evidence) with chunk_id cross-reference.

Usage:
    uv run python scripts/export_p0_layered_trace.py \\
        --out-json reports/retrieval/phase10_p0_layered_traces.json

Minimal reporting change — no retrieval algorithm, RRF, query builder,
or embedding provider modified.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any

from ticketpilot.evaluation.loaders import (
    load_golden_expectations,
    load_tickets_eval,
)
from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.retrieval.embedding_config import load_embedding_config_from_env
from ticketpilot.retrieval.providers import create_embedding_provider
from ticketpilot.schema.ticket import RawTicket


def _serialize_trace(t) -> dict[str, Any]:
    """Serialize full RetrievalTrace to dict for JSON export."""
    return {
        "keyword_results": [
            {
                "chunk_id": str(r.chunk_id),
                "doc_id": str(r.doc_id),
                "doc_type": r.doc_type.value if hasattr(r.doc_type, "value") else str(r.doc_type),
                "score": r.score,
                "rank": r.rank,
                "search_method": r.search_method,
            }
            for r in t.keyword_results
        ],
        "vector_results": [
            {
                "chunk_id": str(r.chunk_id),
                "doc_id": str(r.doc_id),
                "doc_type": r.doc_type.value if hasattr(r.doc_type, "value") else str(r.doc_type),
                "score": r.score,
                "rank": r.rank,
                "embedding_provider": r.embedding_provider,
            }
            for r in t.vector_results
        ],
        "fused_results": [
            {
                "chunk_id": str(r.chunk_id),
                "doc_id": str(r.doc_id),
                "doc_type": r.doc_type.value if hasattr(r.doc_type, "value") else str(r.doc_type),
                "rrf_score": r.rrf_score,
                "keyword_rank": r.keyword_rank,
                "keyword_contribution": r.keyword_contribution,
                "vector_rank": r.vector_rank,
                "vector_contribution": r.vector_contribution,
                "sources": r.sources,
            }
            for r in t.fused_results
        ],
        "final_evidence_ids": [str(eid) for eid in t.final_evidence_ids],
        "keyword_count": len(t.keyword_results),
        "vector_count": len(t.vector_results),
        "fused_count": len(t.fused_results),
        "total_latency_ms": t.total_latency_ms,
        "embedding_provider": t.embedding_provider,
    }


# P0-related wrong cases from Phase 9.4.1 knowledge expansion
# Each entry maps case_id → set of P0 record doc_ids that were added
P0_RELATED_CASES: dict[str, list[str]] = {
    "case_retu_004": ["f0f0f0f0-2222-2222-2222-222222222222"],
    "case_refu_001": ["ae0e0e0e-aaaa-aaaa-aaaa-aaaaaaaaaaaa"],
    "case_refu_006": ["ae0e0e0e-aaaa-aaaa-aaaa-aaaaaaaaaaaa"],
    "case_acco_003": [
        "ae0e0e0e-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        "ca0a0a0a-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
    ],
    "case_acco_006": ["ae0e0e0e-bbbb-bbbb-bbbb-bbbbbbbbbbbb"],
    "case_acco_012": ["ae0e0e0e-bbbb-bbbb-bbbb-bbbbbbbbbbbb"],
    "case_refu_013": [
        "ae0e0e0e-cccc-cccc-cccc-cccccccccccc",
        "ca0a0a0a-6666-6666-6666-666666666666",
    ],
    "case_refu_009": ["ae0e0e0e-dddd-dddd-dddd-dddddddddddd"],
    "case_comp_001": ["ca0a0a0a-5555-5555-5555-555555555555"],
    "case_comp_002": ["ca0a0a0a-6666-6666-6666-666666666666"],
    "case_comp_003": ["ca0a0a0a-7777-7777-7777-777777777777"],
    "case_comp_008": ["ca0a0a0a-8888-8888-8888-888888888888"],
    "case_comp_004": ["ca0a0a0a-9999-9999-9999-999999999999"],
    "case_comp_009": ["ca0a0a0a-9999-9999-9999-999999999999"],
}


def main() -> None:
    args = _parse_args()
    tickets = load_tickets_eval(args.tickets)
    golden = load_golden_expectations(args.golden)

    # Build embedding provider from env
    try:
        config = load_embedding_config_from_env()
        embedding_provider = create_embedding_provider(config)
    except Exception as e:
        print(f"Warning: using default embedding provider ({e})", file=sys.stderr)
        embedding_provider = None

    provider_name = (
        getattr(embedding_provider, "__class__", None).__name__
        if embedding_provider
        else "none"
    )
    print(f"Embedding provider: {provider_name}")

    cases_out: list[dict[str, Any]] = []
    for case_id in sorted(P0_RELATED_CASES.keys()):
        if case_id not in tickets or case_id not in golden:
            print(f"  SKIP {case_id}: missing from tickets or golden", file=sys.stderr)
            continue

        ticket = tickets[case_id]
        g = golden[case_id]
        p0_ids = P0_RELATED_CASES[case_id]

        raw = RawTicket(
            original_text=ticket.original_text,
            submitted_at=datetime.utcnow(),
            customer_id=ticket.customer_id,
        )
        output = intake_risk_pipeline(raw, embedding_provider=embedding_provider)

        trace_data = {}
        trace_available = output.retrieval_trace is not None
        if trace_available:
            trace_data = _serialize_trace(output.retrieval_trace)

        docs = []
        for i, cand in enumerate(output.evidence_candidates, start=1):
            docs.append({
                "chunk_id": str(cand.chunk_id),
                "doc_id": str(cand.doc_id),
                "doc_type": cand.doc_type.value if hasattr(cand.doc_type, "value") else str(cand.doc_type),
                "rank": i,
                "score": cand.score,
            })

        # Cross-reference P0 chunk_ids against each trace layer
        p0_cross_ref: dict[str, dict[str, Any]] = {}
        for p0_id in p0_ids:
            entry: dict[str, Any] = {
                "p0_record_id": p0_id,
                "keyword_hit": False,
                "keyword_best_rank": None,
                "vector_hit": False,
                "vector_best_rank": None,
                "fused_hit": False,
                "fused_best_rank": None,
                "fused_best_rrf_score": None,
                "final_evidence_hit": False,
                "final_evidence_best_rank": None,
                "sources": [],
            }

            if trace_available:
                t = output.retrieval_trace

                # Check keyword results
                for kr in t.keyword_results:
                    if str(kr.doc_id) == p0_id or str(kr.chunk_id) == p0_id:
                        entry["keyword_hit"] = True
                        if entry["keyword_best_rank"] is None or kr.rank < entry["keyword_best_rank"]:
                            entry["keyword_best_rank"] = kr.rank

                # Check vector results
                for vr in t.vector_results:
                    if str(vr.doc_id) == p0_id or str(vr.chunk_id) == p0_id:
                        entry["vector_hit"] = True
                        if entry["vector_best_rank"] is None or vr.rank < entry["vector_best_rank"]:
                            entry["vector_best_rank"] = vr.rank

                # Check fused results
                for fr in t.fused_results:
                    if str(fr.doc_id) == p0_id or str(fr.chunk_id) == p0_id:
                        entry["fused_hit"] = True
                        rank = next(
                            (i for i, r in enumerate(t.fused_results) if r.chunk_id == fr.chunk_id),
                            None,
                        )
                        if rank is not None:
                            fused_rank = rank + 1
                        else:
                            fused_rank = None
                        if entry["fused_best_rank"] is None or (
                            fused_rank is not None and fused_rank < entry["fused_best_rank"]
                        ):
                            entry["fused_best_rank"] = fused_rank
                            entry["fused_best_rrf_score"] = fr.rrf_score
                        entry["sources"] = list(set(entry["sources"] + fr.sources))

                # Check final evidence
                for idx, eid in enumerate(t.final_evidence_ids):
                    # Look up the chunk's doc_id
                    chunk_doc_id = None
                    for kr in t.keyword_results:
                        if kr.chunk_id == eid:
                            chunk_doc_id = str(kr.doc_id)
                            break
                    if chunk_doc_id is None:
                        for vr in t.vector_results:
                            if vr.chunk_id == eid:
                                chunk_doc_id = str(vr.doc_id)
                                break
                    if chunk_doc_id is None:
                        for fr in t.fused_results:
                            if fr.chunk_id == eid:
                                chunk_doc_id = str(fr.doc_id)
                                break
                    if chunk_doc_id == p0_id or str(eid) == p0_id:
                        entry["final_evidence_hit"] = True
                        if entry["final_evidence_best_rank"] is None or (idx + 1) < entry["final_evidence_best_rank"]:
                            entry["final_evidence_best_rank"] = idx + 1

            p0_cross_ref[p0_id] = entry

        case_entry = {
            "case_id": case_id,
            "query": ticket.original_text,
            "expected_doc_types": sorted(g.expected_evidence_doc_types),
            "p0_record_ids": p0_ids,
            "retrieved_docs": docs,
            "p0_cross_reference": p0_cross_ref,
            "trace_data": trace_data,
            "trace_available": trace_available,
        }
        cases_out.append(case_entry)
        print(f"  OK {case_id}: {len(docs)} docs, trace={'yes' if trace_available else 'no'}, p0={len(p0_ids)} ids")

    out = pathlib.Path(args.out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "provider": provider_name,
            "total_cases": len(cases_out),
            "cases": cases_out,
        }, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\nExported {len(cases_out)} P0-related cases to {args.out_json}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 10.3 P0 Layered Trace Export")
    parser.add_argument("--tickets", default="data/eval/tickets_eval.csv")
    parser.add_argument("--golden", default="data/eval/golden_expectations.csv")
    parser.add_argument("--out-json", default="reports/retrieval/phase10_p0_layered_traces.json")
    return parser.parse_args()


if __name__ == "__main__":
    main()
