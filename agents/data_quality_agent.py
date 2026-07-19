from __future__ import annotations

from typing import Any


def explain_quality(quality: dict[str, Any]) -> list[str]:
    issues = quality.get("issues") or []
    if not issues:
        return ["未发现阻断性数据质量问题，可以进入指标计算。"]
    lines = []
    for issue in issues[:8]:
        level = issue.get("severity", "warning")
        fields = "、".join(issue.get("fields") or []) or "多字段"
        lines.append(
            f"{level}：{issue.get('issue_type')} 影响 {fields}，"
            f"影响行数 {issue.get('affected_rows', 0)}，建议：{issue.get('suggestion', '')}"
        )
    return lines

