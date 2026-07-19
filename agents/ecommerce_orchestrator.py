from __future__ import annotations

from typing import Any

import pandas as pd

from agents.data_quality_agent import explain_quality
from agents.diagnosis_agent import summarize_diagnoses
from agents.metric_analysis_agent import summarize_metrics
from agents.recommendation_agent import action_items
from diagnosis.rule_engine import run_diagnosis
from services.data_quality_service import run_quality_checks
from services.metric_service import build_metric_context


def run_workflow(datasets: dict[str, pd.DataFrame], *, current_period: dict[str, str] | None = None) -> dict[str, Any]:
    quality = run_quality_checks(datasets)
    metric_context = build_metric_context(datasets, current_period=current_period)
    diagnoses = [] if quality.get("blocking") else [item.to_dict() for item in run_diagnosis(metric_context, quality)]
    actions = action_items(diagnoses)
    return {
        "quality": quality,
        "quality_explanation": explain_quality(quality),
        "metric_context": metric_context,
        "metric_summary": summarize_metrics(metric_context),
        "diagnoses": diagnoses,
        "diagnosis_summary": summarize_diagnoses(diagnoses),
        "actions": actions,
    }

