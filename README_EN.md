# DataScout Agent · AI Data Analysis Workspace

<p align="center">
  <img src="./static/Images/icon.png" alt="DataScout Agent" width="112" />
</p>

<p align="center">
  <strong>Turn spreadsheets, databases, and business APIs into traceable analysis and reusable deliverables.</strong>
</p>

<p align="center">
  <a href="./README.md">中文</a> ·
  <a href="#quick-start">Quick Start</a> ·
  <a href="./ARCHITECTURE.md">Architecture</a> ·
  <a href="./DEPLOYMENT.md">Deployment</a>
</p>

## What it is

DataScout Agent is a conversational AI workspace for business data analysis. Connect Excel / CSV files, SQL databases, Google Sheets, HTTP APIs, or a local workspace; ask questions in natural language; then inspect the queries, tool execution, tables, charts, and conclusions in one interface.

The system keeps analytical work observable. Users can see which source is active, which tool is running, what data supports a result, and which artifact was produced. Deterministic metric, data-quality, and rule engines are available when calculations must remain independent from the language model.

## Highlights

| Capability | Product value |
| --- | --- |
| Multi-source context | Analyze files, databases, online sheets, APIs, and local workspace data in one session |
| Streaming AI analysis | Follow tool activity, tables, charts, reasoning status, retries, and follow-up questions |
| 22 built-in skills | SQL, cleaning, regression, clustering, forecasting, visualization, reports, PowerPoint, and dashboards |
| Visible data scope | Preview schemas and rows, then explicitly select the tables used by the current turn |
| Deliverable outputs | Export datasets, Excel workbooks, reports, presentations, charts, and interactive dashboards |
| Background jobs | Monitor progress, cancel long-running operations, recover results, and download artifacts |
| Business knowledge | Maintain metric definitions, business rules, context notes, and imported knowledge files |
| Local-first storage | Keep uploads, sessions, credentials, and generated artifacts outside the repository |

## User flow

```mermaid
flowchart LR
    A[Connect data] --> B[Preview data]
    B --> C[Ask a question]
    C --> D[Agent planning]
    D --> E[Run analysis]
    E --> F[Tables and charts]
    F --> G[Validate results]
    G --> H[Export deliverables]

    classDef step fill:#F3F1FF,stroke:#8B5CF6,color:#1F2937,stroke-width:1px
    class A,B,C,D,E,F,G,H step
```

## Quick start

Requirements: Python 3.10+. Node.js is only required when rebuilding the frontend.

```bash
git clone https://github.com/uuuuuu11/data-analysis-agent.git
cd data-analysis-agent

python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS / Linux: source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env        # Windows PowerShell: Copy-Item .env.example .env
python app.py
```

Open <http://localhost:5001/>. The health endpoint is <http://localhost:5001/api/health>.

## Managed AI service

The delivered product connects to its AI service on the server. End users do not enter an endpoint, model name, or API key—they can open the workspace and start analyzing data immediately.

Production credentials are never included in the public repository. For self-hosting, an administrator provisions the model service on the server as described in [DEPLOYMENT.md](./DEPLOYMENT.md); those settings are not exposed to browsers or regular users.

## How to use it

1. Select **Add data** and upload a file or connect a source.
2. Open **Data Preview** to inspect schemas, sample rows, and active tables.
3. Ask a question directly or choose an explicit analysis skill.
4. Validate tool activity, tables, and charts, then continue with follow-up questions.
5. Download the generated artifact or save the analysis session.

Example questions:

```text
Summarize revenue by region and create a descending bar chart.
Check this dataset for missing values, duplicates, and outliers.
Compare the last 12 months and explain the largest changes.
Cluster customers with K-Means and describe each segment.
Turn this analysis into an executive report.
```

The **Use sample data** action provides an immediate product walkthrough without private data.

## Data connectors

- Excel / CSV (`.xlsx`, `.xls`, `.csv`)
- SQLAlchemy databases, including MySQL, PostgreSQL, SQLite, and SQL Server
- Google Sheets with a service account
- HTTP APIs with no auth, Bearer Token, or `X-API-Key`
- Local workspaces with explicit read-only or read/write permission

## Architecture

```mermaid
flowchart LR
    UI[AI analysis workspace] --> WEB[Flask Web / REST / SSE]
    WEB --> AGENT[Agent orchestration]
    AGENT --> TOOLS[Controlled analysis tools]
    TOOLS --> DATA[DuckDB / local workspace]

    WEB --> ACCOUNT[Accounts and preferences]
    AGENT -.-> MODEL[Managed model service]
    TOOLS -.-> SOURCE[Excel / CSV / SQL / Sheets / API]
    TOOLS --> OUTPUT[Jobs and analysis artifacts]

    classDef primary fill:#F3F1FF,stroke:#8B5CF6,color:#1F2937,stroke-width:1px
    classDef support fill:#F8FAFC,stroke:#A78BFA,color:#374151,stroke-width:1px
    class UI,WEB,AGENT,TOOLS,DATA primary
    class ACCOUNT,MODEL,SOURCE,OUTPUT support
```

The frontend uses Flask templates, modular JavaScript, progressive Vue islands, and Vite. The backend combines Flask, Waitress, pandas, DuckDB, SQLAlchemy, sqlglot, background jobs, local authentication, and structured Agent tooling. See [ARCHITECTURE.md](./ARCHITECTURE.md) for details.

## Docker

```bash
cp .env.example .env
cp Caddyfile.example Caddyfile
docker compose up -d --build
```

Runtime data is persisted in `runtime-data/`. See [DEPLOYMENT.md](./DEPLOYMENT.md) for HTTPS, backup, and operations guidance.

## Verification

```bash
python -m unittest Test.test_api_smoke Test.test_validate Test.test_ecommerce_metrics
pnpm install --frozen-lockfile
pnpm quality
```

## Security and privacy

Model credentials are managed on the server and never exposed to the browser or committed to the repository. SQL is guarded by AST-level read-only validation, sensitive workspace paths are blocked, and browser responses use restrictive security headers. The server sends the context required for an answer to the managed model service; enterprise deployments can select an integration that matches their data policy.

See [SECURITY.md](./SECURITY.md) for responsible disclosure.
