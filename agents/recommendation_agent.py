from __future__ import annotations

from typing import Any


def action_items(diagnoses: list[dict[str, Any]]) -> list[dict[str, Any]]:
    items = []
    for diagnosis in diagnoses:
        priority = "高" if diagnosis.get("severity") == "high" else "中"
        recs = diagnosis.get("recommendations") or []
        items.append({
            "priority": priority,
            "diagnosis": diagnosis.get("title", ""),
            "rule_id": diagnosis.get("rule_id", ""),
            "recommendation": recs[0] if recs else "继续观察该异常，并补充更多维度数据。",
            "confidence": diagnosis.get("confidence", 0),
        })
    return sorted(items, key=lambda item: (0 if item["priority"] == "高" else 1, -float(item["confidence"] or 0)))

