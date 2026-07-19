# Test Suite

项目使用 Python 标准库 `unittest`，覆盖公开仓库中的核心产品能力。外部 LLM、Google Sheets 和真实数据库不会在测试中被调用；相关场景使用 Fake、临时文件或内存数据源。

## 运行

```bash
python -m unittest discover -s Test -p "test_*.py" -v
```

运行单个模块：

```bash
python -m unittest Test.test_validate -v
```

CI 使用的核心回归集：

```bash
python -m unittest \
  Test.test_api_smoke \
  Test.test_validate \
  Test.test_ecommerce_metrics \
  Test.test_schema_mapper \
  Test.test_data_quality_service \
  Test.test_diagnosis_rules \
  -v
```

## 覆盖范围

| 领域 | 代表性测试 |
| --- | --- |
| 应用与 API | Flask 启动、公开端点、HTML action 映射、跨站写保护 |
| Agent 与工具 | 工具 Schema、动态暴露、激活契约、重试、推理流与结果恢复 |
| 数据源 | CSV / Excel、预览选表、多源上下文、异步解析和数据质量 |
| SQL 安全 | AST 只读校验、危险语句阻断、参数与表名验证 |
| Skills 与 Commands | 三层加载、热更新、意图路由、Markdown 命令与权限收窄 |
| Workspace | 路径越界、敏感目录屏蔽、只读/可编辑权限和文件竞态保护 |
| 后台任务 | 队列、取消、事件流、历史记录和产物恢复 |
| 知识与偏好 | 本地 RAG、引用、用户偏好、配额和临时 Prompt |
| 分析能力 | 图表选择、指标计算、字段映射、诊断规则和时间序列任务 |
| 输出 | Excel、图表与分析产物生成 |

`test_smoke_all.py` 会端到端生成完整图表集合，执行时间较长，适合在发布前单独运行。

## 约定

- 测试文件命名为 `test_<module>.py`。
- 每个测试模块均可通过 `python -m unittest Test.test_<module> -v` 独立运行。
- 测试数据必须匿名且可在仓库内重建。
- 需要网络或真实凭据的行为必须使用 Mock，不得在 CI 中读取本地 `.env`。
