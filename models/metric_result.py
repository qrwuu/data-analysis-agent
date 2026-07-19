from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricResult:
    metric_id: str
    name: str
    value: float | int | None
    formatted: str
    formula: str
    source: str
    time_range: dict[str, str] = field(default_factory=dict)
    raw_values: dict[str, Any] = field(default_factory=dict)
    unit: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "name": self.name,
            "value": self.value,
            "formatted": self.formatted,
            "formula": self.formula,
            "source": self.source,
            "time_range": self.time_range,
            "raw_values": self.raw_values,
            "unit": self.unit,
        }

