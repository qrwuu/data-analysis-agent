from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class QualityIssue:
    severity: str
    issue_type: str
    fields: list[str]
    affected_rows: int
    affected_ratio: float
    risk: str
    suggestion: str
    auto_fixed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "severity": self.severity,
            "issue_type": self.issue_type,
            "fields": self.fields,
            "affected_rows": self.affected_rows,
            "affected_ratio": self.affected_ratio,
            "risk": self.risk,
            "suggestion": self.suggestion,
            "auto_fixed": self.auto_fixed,
        }


@dataclass
class DiagnosisResult:
    title: str
    severity: str
    affected_metrics: list[str]
    current_value: Any
    comparison_value: Any
    change: Any
    products: list[str]
    rule_id: str
    evidence: list[dict[str, Any]]
    possible_causes: list[str]
    recommendations: list[str]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "severity": self.severity,
            "affected_metrics": self.affected_metrics,
            "current_value": self.current_value,
            "comparison_value": self.comparison_value,
            "change": self.change,
            "products": self.products,
            "rule_id": self.rule_id,
            "evidence": self.evidence,
            "possible_causes": self.possible_causes,
            "recommendations": self.recommendations,
            "confidence": self.confidence,
        }

