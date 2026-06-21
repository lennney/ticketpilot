"""Confidence distribution monitoring dashboard page.

Runs the pipeline on eval tickets and renders 4 visualizations:
1. Confidence distribution histogram
2. Confidence tier pie chart (HIGH / MEDIUM / LOW / CRITICAL)
3. Agent routing distribution bar chart
4. Risk flag heatmap
"""

from __future__ import annotations

import csv
import pathlib
from collections import Counter
from dataclasses import dataclass
from datetime import datetime

import plotly.express as px
import streamlit as st

from ticketpilot.confidence.scorer import ConfidenceLevel
from ticketpilot.degradation.router import ResponseStrategy
from ticketpilot.pipeline import intake_risk_pipeline, post_process
from ticketpilot.schema.ticket import RawTicket, RiskFlag

EVAL_TICKETS_PATH = pathlib.Path("data/eval/tickets_eval.csv")


@dataclass(frozen=True)
class TicketMetrics:
    """Aggregated metrics for a single processed ticket."""

    case_id: str
    confidence: float
    confidence_level: ConfidenceLevel
    strategy: ResponseStrategy
    intent: str
    risk_flags: frozenset[RiskFlag]
    severity: str
    must_human_review: bool


def _load_raw_tickets(
    path: pathlib.Path = EVAL_TICKETS_PATH,
) -> list[tuple[str, RawTicket]]:
    """Load eval CSV into (case_id, RawTicket) pairs."""
    tickets: list[tuple[str, RawTicket]] = []
    with path.open(newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            case_id = row["case_id"].strip()
            raw = RawTicket(
                original_text=row["original_text"].strip(),
                submitted_at=datetime.fromisoformat(
                    row["submitted_at"].replace("Z", "+00:00")
                ),
                customer_id=row.get("customer_id", "").strip() or None,
            )
            tickets.append((case_id, raw))
    return tickets


def run_pipeline_on_eval_tickets(
    path: pathlib.Path = EVAL_TICKETS_PATH,
) -> list[TicketMetrics]:
    """Run the full pipeline on all eval tickets and return metrics."""
    pairs = _load_raw_tickets(path)
    results: list[TicketMetrics] = []

    for case_id, raw_ticket in pairs:
        output = intake_risk_pipeline(raw_ticket)
        confidence, degraded = post_process(output)

        results.append(
            TicketMetrics(
                case_id=case_id,
                confidence=confidence.overall,
                confidence_level=confidence.level,
                strategy=degraded.strategy,
                intent=output.classification.intent.value,
                risk_flags=frozenset(output.risk_assessment.flags),
                severity=output.risk_assessment.severity.value,
                must_human_review=output.risk_assessment.must_human_review,
            )
        )

    return results


def build_risk_matrix(results: list[TicketMetrics]) -> dict[str, dict[str, int]]:
    """Build a risk-flag × intent matrix for heatmap display."""
    intents = sorted({r.intent for r in results})
    all_flags: set[RiskFlag] = set()
    for r in results:
        all_flags |= r.risk_flags
    flag_names = sorted(f.value for f in all_flags)

    matrix: dict[str, dict[str, int]] = {}
    for flag in flag_names:
        row: dict[str, int] = {}
        for intent in intents:
            count = sum(
                1
                for r in results
                if intent == r.intent and any(f.value == flag for f in r.risk_flags)
            )
            row[intent] = count
        matrix[flag] = row

    return matrix


def render_metrics_page(results: list[TicketMetrics] | None = None) -> None:
    """Render the confidence monitoring page in Streamlit."""
    st.header("置信度监控")

    if results is None:
        with st.spinner("正在处理 101 张评估工单..."):
            results = run_pipeline_on_eval_tickets()

    confidences = [r.confidence for r in results]

    # 1. Confidence distribution histogram
    st.subheader("置信度分布")
    fig_hist = px.histogram(
        x=confidences,
        nbins=20,
        labels={"x": "置信度", "y": "工单数"},
        color_discrete_sequence=["#4A90D9"],
    )
    fig_hist.update_layout(
        xaxis_title="置信度",
        yaxis_title="工单数",
        showlegend=False,
    )
    st.plotly_chart(fig_hist, use_container_width=True)

    # 2. Tier pie chart
    st.subheader("分级分布")
    tier_counts = Counter(r.confidence_level.value for r in results)
    tier_colors = {
        "high": "#2ECC71",
        "medium": "#F39C12",
        "low": "#E67E22",
        "critical": "#E74C3C",
    }
    fig_pie = px.pie(
        names=list(tier_counts.keys()),
        values=list(tier_counts.values()),
        color=list(tier_counts.keys()),
        color_discrete_map=tier_colors,
    )
    fig_pie.update_traces(textinfo="percent+label")
    st.plotly_chart(fig_pie, use_container_width=True)

    # 3. Strategy routing bar chart
    st.subheader("Agent 路由分布")
    strategy_counts = Counter(r.strategy.value for r in results)
    fig_bar = px.bar(
        x=list(strategy_counts.keys()),
        y=list(strategy_counts.values()),
        labels={"x": "路由策略", "y": "工单数"},
        color=list(strategy_counts.keys()),
        color_discrete_sequence=["#2ECC71", "#F39C12", "#E67E22", "#E74C3C"],
    )
    fig_bar.update_layout(showlegend=False)
    st.plotly_chart(fig_bar, use_container_width=True)

    # 4. Risk flag heatmap
    st.subheader("风险标签分布")
    risk_matrix = build_risk_matrix(results)
    if risk_matrix:
        import pandas as pd

        flags = sorted(risk_matrix.keys())
        intents = sorted({intent for row in risk_matrix.values() for intent in row})
        data = []
        for flag in flags:
            for intent in intents:
                data.append(
                    {
                        "风险标签": flag,
                        "意图": intent,
                        "数量": risk_matrix[flag].get(intent, 0),
                    }
                )
        df = pd.DataFrame(data)
        pivot = df.pivot(index="风险标签", columns="意图", values="数量").fillna(0)
        fig_heat = px.imshow(
            pivot,
            labels=dict(x="意图", y="风险标签", color="数量"),
            color_continuous_scale="OrRd",
            aspect="auto",
        )
        st.plotly_chart(fig_heat, use_container_width=True)
    else:
        st.info("无风险标签数据")
