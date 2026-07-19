from __future__ import annotations

import html
from datetime import datetime
from pathlib import Path
from typing import Any


DISCLAIMER = "本系统基于用户上传的数据提供经营分析辅助，不保证建议一定带来经营收益。请结合实际业务情况进行判断。"


def render_report_html(project: dict[str, Any], metric_context: dict[str, Any], diagnoses: list[dict[str, Any]], actions: list[dict[str, Any]]) -> str:
    cards = metric_context.get("cards") or []
    rows = "\n".join(
        f"<tr><td>{html.escape(str(card.get('name')))}</td><td>{html.escape(str(card.get('formatted')))}</td><td>{html.escape(str(card.get('formula')))}</td></tr>"
        for card in cards
    )
    diagnosis_html = "\n".join(
        "<section class='diag'>"
        f"<h3>{html.escape(str(item.get('title')))}</h3>"
        f"<p>规则：{html.escape(str(item.get('rule_id')))}｜严重程度：{html.escape(str(item.get('severity')))}｜可信度：{html.escape(str(item.get('confidence')))}</p>"
        f"<p>{html.escape(str(item.get('possible_causes') or ''))}</p>"
        "</section>"
        for item in diagnoses
    ) or "<p>未命中预设异常规则。</p>"
    action_html = "\n".join(
        f"<li><strong>{html.escape(str(item.get('priority')))}</strong> {html.escape(str(item.get('diagnosis')))}：<pre>{html.escape(str(item.get('recommendation')))}</pre></li>"
        for item in actions
    ) or "<li>暂无行动建议。</li>"
    period = metric_context.get("current_period") or {}
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>数探 Agent 经营诊断报告</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif; margin: 32px; color: #172033; }}
    h1 {{ margin-bottom: 4px; }}
    .meta {{ color: #667085; margin-bottom: 24px; }}
    table {{ width: 100%; border-collapse: collapse; margin: 16px 0 28px; }}
    th, td {{ border: 1px solid #d9e1ec; padding: 10px; text-align: left; }}
    th {{ background: #f5f7fb; }}
    .diag {{ border: 1px solid #d9e1ec; border-radius: 8px; padding: 14px; margin: 12px 0; }}
    pre {{ white-space: pre-wrap; font-family: inherit; background: #f8fafc; padding: 10px; border-radius: 6px; }}
    .disclaimer {{ margin-top: 28px; color: #667085; font-size: 13px; }}
  </style>
</head>
<body>
  <h1>数探 Agent 经营诊断报告</h1>
  <div class="meta">项目：{html.escape(str(project.get('name') or '数探项目'))}｜周期：{html.escape(str(period.get('start', '')))} 至 {html.escape(str(period.get('end', '')))}｜生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
  <h2>核心指标</h2>
  <table><thead><tr><th>指标</th><th>结果</th><th>公式</th></tr></thead><tbody>{rows}</tbody></table>
  <h2>诊断结果</h2>
  {diagnosis_html}
  <h2>行动清单</h2>
  <ol>{action_html}</ol>
  <p class="disclaimer">{DISCLAIMER}</p>
</body>
</html>"""


def save_report(project: dict[str, Any], metric_context: dict[str, Any], diagnoses: list[dict[str, Any]], actions: list[dict[str, Any]], report_dir: Path) -> dict[str, Any]:
    report_dir.mkdir(parents=True, exist_ok=True)
    report_id = datetime.now().strftime("report_%Y%m%d_%H%M%S")
    filename = f"{report_id}.html"
    path = report_dir / filename
    path.write_text(render_report_html(project, metric_context, diagnoses, actions), encoding="utf-8")
    return {
        "report_id": report_id,
        "filename": filename,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "format": "html",
    }

