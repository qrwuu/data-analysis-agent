from __future__ import annotations

import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from flask import Blueprint, abort, jsonify, request, send_file
from werkzeug.utils import secure_filename

from agents.ecommerce_orchestrator import run_workflow
from agents.recommendation_agent import action_items
from agents.report_agent import save_report
from infrastructure.paths import data_path, resource_path
from models.ecommerce_project import DATASET_ROLES, DatasetState, EcommerceProject, FieldMapping
from services.data_quality_service import run_quality_checks
from services.metric_service import build_metric_context
from services.schema_mapper import (
    infer_field_mapping,
    mapping_from_payload,
    missing_required_fields,
    normalize_dataframe,
)


bp = Blueprint("ecommerce", __name__)

PROJECTS_DIR = data_path("outputs", "ecommerce", "projects")
PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_ROWS = 200_000
ASK_ROW_LIMIT = 500


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _project_dir(project_id: str) -> Path:
    safe = secure_filename(project_id) or project_id
    return PROJECTS_DIR / safe


def _project_file(project_id: str) -> Path:
    return _project_dir(project_id) / "project.json"


def _save_project(project: EcommerceProject) -> None:
    project.updated_at = _now()
    root = _project_dir(project.project_id)
    root.mkdir(parents=True, exist_ok=True)
    tmp = root / ".project.json.tmp"
    tmp.write_text(json.dumps(project.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(root / "project.json")


def _load_project(project_id: str) -> EcommerceProject:
    path = _project_file(project_id)
    if not path.is_file():
        abort(404, description="项目不存在")
    return EcommerceProject.from_dict(json.loads(path.read_text(encoding="utf-8")))


def _allowed_file(filename: str) -> bool:
    return Path(filename or "").suffix.lower() in ALLOWED_EXTENSIONS


def _read_frame(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        df = pd.read_csv(path)
    elif suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
    else:
        raise ValueError("仅支持 CSV / XLSX / XLS 文件")
    if len(df) > MAX_ROWS:
        raise ValueError(f"单表最多支持 {MAX_ROWS} 行")
    return df


def _preview(df: pd.DataFrame, limit: int = 20) -> list[dict[str, Any]]:
    return df.head(limit).where(pd.notna(df), None).to_dict(orient="records")


def _date_range(df: pd.DataFrame) -> dict[str, str]:
    if "date" not in df.columns or df.empty:
        return {}
    dates = pd.to_datetime(df["date"], errors="coerce").dropna()
    if dates.empty:
        return {}
    return {"start": dates.min().strftime("%Y-%m-%d"), "end": dates.max().strftime("%Y-%m-%d")}


def _dataset_frame(project: EcommerceProject, role: str) -> pd.DataFrame:
    state = project.datasets.get(role)
    if state is None or not state.stored_path:
        return pd.DataFrame()
    path = Path(state.stored_path)
    if not path.is_file():
        return pd.DataFrame()
    return _read_frame(path)


def _normalized_datasets(project: EcommerceProject) -> dict[str, pd.DataFrame]:
    result: dict[str, pd.DataFrame] = {}
    for role in DATASET_ROLES:
        state = project.datasets.get(role)
        if state is None:
            continue
        missing = missing_required_fields(role, state.mapping)
        if missing:
            continue
        raw = _dataset_frame(project, role)
        if raw.empty:
            continue
        normalized = normalize_dataframe(role, raw, state.mapping)
        if "date" in normalized.columns:
            normalized["date"] = pd.to_datetime(normalized["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        result[role] = normalized
    return result


def _write_normalized_duckdb(project: EcommerceProject, datasets: dict[str, pd.DataFrame]) -> None:
    """Best-effort DuckDB persistence; requirements provide duckdb in supported envs."""
    try:
        import duckdb
    except Exception:
        return
    db_path = _project_dir(project.project_id) / "normalized.duckdb"
    conn = duckdb.connect(str(db_path))
    try:
        for role, df in datasets.items():
            conn.register("_tmp_df", df)
            conn.execute(f'CREATE OR REPLACE TABLE "{role}" AS SELECT * FROM _tmp_df')
            conn.unregister("_tmp_df")
    finally:
        conn.close()


def _store_dataset(project: EcommerceProject, role: str, src_path: Path, display_name: str, *, confirm_mapping: bool = False) -> DatasetState:
    df = _read_frame(src_path)
    mapping = infer_field_mapping(role, df)
    if confirm_mapping:
        for item in mapping.values():
            item.confirmed = bool(item.source_field)
            item.confidence = 1.0 if item.source_field else item.confidence
            item.missing = item.required and not item.source_field
    state = DatasetState(
        role=role,
        filename=display_name,
        stored_path=str(src_path),
        row_count=len(df),
        columns=[str(col) for col in df.columns],
        preview=_preview(df),
        mapping=mapping,
    )
    normalized = normalize_dataframe(role, df, mapping)
    state.date_range = _date_range(normalized)
    project.datasets[role] = state
    return state


def _create_project(name: str = "数探项目") -> EcommerceProject:
    project_id = f"ec_{uuid.uuid4().hex[:12]}"
    now = _now()
    project = EcommerceProject(project_id=project_id, name=name or "数探项目", created_at=now, updated_at=now)
    root = _project_dir(project_id)
    (root / "raw").mkdir(parents=True, exist_ok=True)
    (root / "reports").mkdir(parents=True, exist_ok=True)
    _save_project(project)
    return project


def _ask_response(question: str, metric_context: dict[str, Any], diagnoses: list[dict[str, Any]]) -> dict[str, Any]:
    text = str(question or "").strip()
    charts = metric_context.get("charts") or {}
    tables_used: list[str] = []
    result_rows: list[dict[str, Any]] = []
    formulas: list[str] = []
    answer = ""
    query_steps = ""

    if any(key in text for key in ("高流量低转化", "转化低")):
        tables_used = ["traffic", "orders"]
        result_rows = (charts.get("high_traffic_low_conversion") or [])[:10]
        formulas = ["支付转化率 = payment_buyers / visitors"]
        answer = "以下商品流量较高但支付转化偏低，建议优先检查商品页承接。"
        query_steps = "按商品聚合 visitors 与 payment_buyers，计算支付转化率后按访客降序和转化率升序排序。"
    elif any(key in text for key in ("推广计划", "减少预算", "ROAS", "roas")):
        tables_used = ["advertising"]
        result_rows = (charts.get("campaign_roas_rank") or [])[:10]
        formulas = ["广告投产比ROAS = ad_revenue / ad_spend"]
        answer = "以下推广计划 ROAS 较低，应优先复盘预算、素材和投放人群。"
        query_steps = "按 campaign_id 聚合 ad_spend 与 ad_revenue，计算 ROAS 并升序排序。"
    elif "退款" in text:
        tables_used = ["orders"]
        result_rows = (charts.get("refund_rank") or [])[:10]
        formulas = ["金额退款率 = 退款金额 / 支付GMV"]
        answer = "退款金额主要集中在以下商品。"
        query_steps = "按商品聚合 refund_amount 和 paid_gmv，计算退款率并按退款金额排序。"
    elif any(key in text for key in ("表现最好", "前三", "三个商品", "排行")):
        tables_used = ["orders"]
        result_rows = (charts.get("product_gmv_rank") or [])[:3]
        formulas = ["支付GMV = 有效支付订单 payment_amount 求和"]
        answer = "本周期 GMV 表现最好的三个商品如下。"
        query_steps = "按商品聚合有效支付订单 GMV 并降序取前三。"
    elif any(key in text for key in ("为什么", "下降", "原因")):
        tables_used = ["orders", "traffic", "advertising"]
        result_rows = diagnoses[:5]
        formulas = ["诊断来自规则引擎命中的指标变化，不由模型猜测。"]
        answer = "本次销售变化的可解释异常如下；可能原因仍需结合商品页、库存、评价等外部信息验证。"
        query_steps = "先计算当前周期和上一周期指标，再运行 R1-R8 经营诊断规则。"
    else:
        tables_used = ["orders", "traffic", "advertising"]
        result_rows = metric_context.get("cards") or []
        formulas = [card.get("formula", "") for card in result_rows if card.get("formula")]
        answer = "以下是当前周期核心经营指标摘要。"
        query_steps = "从已确认字段映射的数据表计算核心指标卡。"

    if not result_rows:
        answer = "当前数据不足，无法判断该问题。请确认三类数据是否已上传并完成字段映射。"

    return {
        "answer": answer,
        "tables_used": tables_used,
        "time_range": metric_context.get("current_period") or {},
        "formulas": formulas[:8],
        "query_steps": query_steps,
        "sql": "由 pandas 确定性聚合执行；未执行用户输入 SQL。",
        "rows": result_rows[:ASK_ROW_LIMIT],
        "chart_suggestion": "表格结果已足够回答问题；如需可在经营驾驶舱查看对应图表。" if result_rows else "",
        "cannot_judge_reason": "" if result_rows else "缺少可计算结果或字段映射未确认。",
    }


@bp.post("/api/ecommerce/projects")
def create_project():
    body = request.get_json(silent=True) or {}
    project = _create_project(str(body.get("name") or "数探项目"))
    return jsonify(project.to_dict())


@bp.post("/api/ecommerce/projects/demo")
def create_demo_project():
    project = _create_project("数探示例项目")
    demo_dir = resource_path("demo_data")
    raw_dir = _project_dir(project.project_id) / "raw"
    for role, filename in {
        "orders": "orders_demo.xlsx",
        "traffic": "traffic_demo.xlsx",
        "advertising": "advertising_demo.xlsx",
    }.items():
        source = demo_dir / filename
        target = raw_dir / filename
        shutil.copyfile(source, target)
        _store_dataset(project, role, target, filename, confirm_mapping=True)
    datasets = _normalized_datasets(project)
    _write_normalized_duckdb(project, datasets)
    workflow = run_workflow(datasets)
    project.quality_issues = workflow["quality"]["issues"]
    project.metrics = workflow["metric_context"]
    project.diagnoses = workflow["diagnoses"]
    project.current_period = workflow["metric_context"].get("current_period") or {}
    project.comparison_period = workflow["metric_context"].get("comparison_period") or {}
    project.status = "diagnosed"
    _save_project(project)
    return jsonify(project.to_dict())


@bp.get("/api/ecommerce/projects/<project_id>")
def get_project(project_id: str):
    return jsonify(_load_project(project_id).to_dict())


@bp.post("/api/ecommerce/projects/<project_id>/datasets/<role>")
def upload_dataset(project_id: str, role: str):
    if role not in DATASET_ROLES:
        return jsonify({"error": "未知数据类型"}), 400
    project = _load_project(project_id)
    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"error": "未选择文件"}), 400
    if not _allowed_file(file.filename):
        return jsonify({"error": "仅支持 CSV / XLSX / XLS 文件"}), 400
    content_length = request.content_length or 0
    if content_length and content_length > MAX_UPLOAD_BYTES + 1024 * 1024:
        return jsonify({"error": "文件过大，单文件最多 20MB"}), 413
    safe_name = secure_filename(file.filename) or f"{role}.xlsx"
    target = _project_dir(project_id) / "raw" / f"{role}_{uuid.uuid4().hex[:8]}_{safe_name}"
    target.parent.mkdir(parents=True, exist_ok=True)
    file.save(target)
    if target.stat().st_size > MAX_UPLOAD_BYTES:
        target.unlink(missing_ok=True)
        return jsonify({"error": "文件过大，单文件最多 20MB"}), 413
    try:
        state = _store_dataset(project, role, target, file.filename)
    except Exception as exc:
        target.unlink(missing_ok=True)
        return jsonify({"error": str(exc)}), 400
    project.status = "mapping"
    _save_project(project)
    return jsonify({"dataset": state.to_dict(), "project": project.to_dict()})


@bp.put("/api/ecommerce/projects/<project_id>/mappings/<role>")
def update_mapping(project_id: str, role: str):
    if role not in DATASET_ROLES:
        return jsonify({"error": "未知数据类型"}), 400
    project = _load_project(project_id)
    state = project.datasets.get(role)
    if state is None:
        return jsonify({"error": "请先上传该类型数据"}), 400
    payload = request.get_json(silent=True) or {}
    state.mapping = mapping_from_payload(role, payload, state.mapping)
    raw = _dataset_frame(project, role)
    normalized = normalize_dataframe(role, raw, state.mapping) if not raw.empty else pd.DataFrame()
    state.date_range = _date_range(normalized)
    project.datasets[role] = state
    project.status = "mapped"
    _save_project(project)
    return jsonify({"dataset": state.to_dict(), "missing_required": missing_required_fields(role, state.mapping)})


@bp.post("/api/ecommerce/projects/<project_id>/quality/check")
def quality_check(project_id: str):
    project = _load_project(project_id)
    datasets = _normalized_datasets(project)
    quality = run_quality_checks(datasets)
    project.quality_issues = quality["issues"]
    project.status = "quality_blocked" if quality.get("blocking") else "quality_passed"
    _save_project(project)
    return jsonify(quality)


@bp.get("/api/ecommerce/projects/<project_id>/dashboard")
def dashboard(project_id: str):
    project = _load_project(project_id)
    datasets = _normalized_datasets(project)
    metric_context = build_metric_context(datasets)
    project.metrics = metric_context
    project.current_period = metric_context.get("current_period") or {}
    project.comparison_period = metric_context.get("comparison_period") or {}
    _write_normalized_duckdb(project, datasets)
    _save_project(project)
    return jsonify(metric_context)


@bp.post("/api/ecommerce/projects/<project_id>/diagnoses")
def diagnose(project_id: str):
    project = _load_project(project_id)
    datasets = _normalized_datasets(project)
    workflow = run_workflow(datasets, current_period=(request.get_json(silent=True) or {}).get("current_period"))
    project.quality_issues = workflow["quality"]["issues"]
    project.metrics = workflow["metric_context"]
    project.diagnoses = workflow["diagnoses"]
    project.current_period = workflow["metric_context"].get("current_period") or {}
    project.comparison_period = workflow["metric_context"].get("comparison_period") or {}
    project.status = "quality_blocked" if workflow["quality"].get("blocking") else "diagnosed"
    _write_normalized_duckdb(project, datasets)
    _save_project(project)
    return jsonify(workflow)


@bp.post("/api/ecommerce/projects/<project_id>/ask")
def ask(project_id: str):
    project = _load_project(project_id)
    body = request.get_json(silent=True) or {}
    question = str(body.get("question") or "")
    datasets = _normalized_datasets(project)
    metric_context = project.metrics or build_metric_context(datasets)
    diagnoses = project.diagnoses
    if not diagnoses:
        workflow = run_workflow(datasets)
        metric_context = workflow["metric_context"]
        diagnoses = workflow["diagnoses"]
    return jsonify(_ask_response(question, metric_context, diagnoses))


@bp.post("/api/ecommerce/projects/<project_id>/reports")
def create_report(project_id: str):
    project = _load_project(project_id)
    datasets = _normalized_datasets(project)
    metric_context = project.metrics or build_metric_context(datasets)
    diagnoses = project.diagnoses
    if not diagnoses:
        workflow = run_workflow(datasets)
        metric_context = workflow["metric_context"]
        diagnoses = workflow["diagnoses"]
    actions = action_items(diagnoses)
    report = save_report(project.to_dict(), metric_context, diagnoses, actions, _project_dir(project_id) / "reports")
    project.reports.insert(0, report)
    _save_project(project)
    return jsonify(report)


@bp.get("/api/ecommerce/projects/<project_id>/reports/<report_id>/download")
def download_report(project_id: str, report_id: str):
    project = _load_project(project_id)
    report = next((item for item in project.reports if item.get("report_id") == report_id), None)
    if not report:
        abort(404)
    filename = Path(str(report.get("filename") or "")).name
    path = _project_dir(project_id) / "reports" / filename
    if not path.is_file():
        abort(404)
    return send_file(path, as_attachment=True, download_name=filename)


@bp.get("/api/ecommerce/templates/<role>")
def download_template(role: str):
    if role not in DATASET_ROLES:
        abort(404)
    filename = {
        "orders": "orders_template.xlsx",
        "traffic": "traffic_template.xlsx",
        "advertising": "advertising_template.xlsx",
    }[role]
    path = resource_path("data_templates", filename)
    if not path.is_file():
        abort(404)
    return send_file(path, as_attachment=True, download_name=filename)

