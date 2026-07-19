from __future__ import annotations

from typing import Any


def explain_diagnosis(item: dict[str, Any]) -> str:
    evidence = item.get("evidence") or []
    facts = []
    for ev in evidence[:3]:
        metric = ev.get("metric") or ev.get("reason") or "证据"
        current = ev.get("current", ev.get("values", ""))
        change = ev.get("change", "")
        facts.append(f"{metric} 当前值 {current}，变化 {change}".strip("，"))
    causes = "、".join(item.get("possible_causes") or ["现有数据无法直接证明具体原因"])
    return (
        "数据已经证明：\n"
        + "\n".join(facts or ["命中了确定性诊断规则。"])
        + "\n\n可能原因：\n"
        + causes
        + "\n\n现有数据无法直接证明具体是哪一个原因。"
    )

