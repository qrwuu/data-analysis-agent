from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


DatasetRole = Literal["orders", "traffic", "advertising"]
DATASET_ROLES: tuple[str, ...] = ("orders", "traffic", "advertising")


@dataclass
class FieldMapping:
    standard_field: str
    source_field: str = ""
    confidence: float = 0.0
    confirmed: bool = False
    required: bool = False
    missing: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "standard_field": self.standard_field,
            "source_field": self.source_field,
            "confidence": self.confidence,
            "confirmed": self.confirmed,
            "required": self.required,
            "missing": self.missing,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "FieldMapping":
        return cls(
            standard_field=str(data.get("standard_field") or ""),
            source_field=str(data.get("source_field") or ""),
            confidence=float(data.get("confidence") or 0),
            confirmed=bool(data.get("confirmed")),
            required=bool(data.get("required")),
            missing=bool(data.get("missing")),
        )


@dataclass
class DatasetState:
    role: str
    filename: str = ""
    stored_path: str = ""
    row_count: int = 0
    columns: list[str] = field(default_factory=list)
    preview: list[dict[str, Any]] = field(default_factory=list)
    mapping: dict[str, FieldMapping] = field(default_factory=dict)
    date_range: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "filename": self.filename,
            "stored_path": self.stored_path,
            "row_count": self.row_count,
            "columns": self.columns,
            "preview": self.preview,
            "mapping": {key: value.to_dict() for key, value in self.mapping.items()},
            "date_range": self.date_range,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DatasetState":
        mapping = {}
        for key, value in (data.get("mapping") or {}).items():
            if isinstance(value, dict):
                mapping[str(key)] = FieldMapping.from_dict(value)
        return cls(
            role=str(data.get("role") or ""),
            filename=str(data.get("filename") or ""),
            stored_path=str(data.get("stored_path") or ""),
            row_count=int(data.get("row_count") or 0),
            columns=[str(item) for item in (data.get("columns") or [])],
            preview=list(data.get("preview") or []),
            mapping=mapping,
            date_range=dict(data.get("date_range") or {}),
        )


@dataclass
class EcommerceProject:
    project_id: str
    name: str
    created_at: str
    updated_at: str
    status: str = "created"
    datasets: dict[str, DatasetState] = field(default_factory=dict)
    quality_issues: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    diagnoses: list[dict[str, Any]] = field(default_factory=list)
    reports: list[dict[str, Any]] = field(default_factory=list)
    current_period: dict[str, str] = field(default_factory=dict)
    comparison_period: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "datasets": {key: value.to_dict() for key, value in self.datasets.items()},
            "quality_issues": self.quality_issues,
            "metrics": self.metrics,
            "diagnoses": self.diagnoses,
            "reports": self.reports,
            "current_period": self.current_period,
            "comparison_period": self.comparison_period,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "EcommerceProject":
        datasets = {}
        for key, value in (data.get("datasets") or {}).items():
            if isinstance(value, dict):
                datasets[str(key)] = DatasetState.from_dict(value)
        return cls(
            project_id=str(data.get("project_id") or ""),
            name=str(data.get("name") or "数探项目"),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
            status=str(data.get("status") or "created"),
            datasets=datasets,
            quality_issues=list(data.get("quality_issues") or []),
            metrics=dict(data.get("metrics") or {}),
            diagnoses=list(data.get("diagnoses") or []),
            reports=list(data.get("reports") or []),
            current_period=dict(data.get("current_period") or {}),
            comparison_period=dict(data.get("comparison_period") or {}),
        )
