# 数探 Agent 部署指南

本文使用 Docker Compose、Caddy 和持久化运行目录部署数探 Agent。应用通过 Caddy 提供 HTTPS，Flask 服务仅在容器网络中暴露。

## 1. 准备主机

推荐配置：

- Linux x86_64 / ARM64 主机；
- 2 vCPU、4 GB 内存起步；
- 已安装 Docker Engine 与 Docker Compose；
- 一个已解析到主机公网 IP 的域名；
- 防火墙开放 80 和 443 端口。

## 2. 准备配置

```bash
git clone https://github.com/uuuuuu11/data-analysis-agent.git
cd data-analysis-agent
cp .env.example .env
cp Caddyfile.example Caddyfile
```

编辑 `.env`，至少设置：

```dotenv
BAA_AUTH_SECRET=replace-with-a-long-random-value
OPENAI_API_KEY=your-provider-key
```

也可以在应用启动后通过模型设置配置兼容提供商。

## 3. 配置 HTTPS 与访问保护

生成 Basic Auth 密码哈希：

```bash
docker run --rm caddy:2-alpine caddy hash-password --plaintext 'replace-with-a-strong-password'
```

编辑 `Caddyfile`：

- 将 `__DOMAIN__` 替换为实际域名；
- 将 `__CADDY_BASIC_AUTH_HASH__` 替换为上一步生成的完整哈希；
- 按需将用户名 `reviewer` 改为自定义值。

不要把明文密码或真实 API Key 写入 Caddyfile、Compose 文件或 Git。

## 4. 启动

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f app
```

健康检查：

```bash
curl -u reviewer:your-password https://your-domain.example/api/health
```

正常响应：

```json
{"ok": true, "service": "datascout-agent", "status": "healthy"}
```

## 5. 持久化与备份

`compose.yaml` 将应用运行数据保存到主机的 `runtime-data/`。这里包含上传文件、会话、账号、知识库、任务和生成产物。

备份前可短暂停止应用写入：

```bash
docker compose stop app
tar -czf datascout-runtime-$(date +%Y%m%d).tar.gz runtime-data
docker compose start app
```

恢复时停止服务，将备份解压为 `runtime-data/`，确认目录权限后重新启动。

## 6. 更新

```bash
git pull --ff-only
docker compose up -d --build
docker image prune -f
```

更新前先备份 `runtime-data/` 和 `.env`。`.env`、`Caddyfile` 与运行数据均不会被 Git 覆盖。

## 7. 常用运维命令

```bash
docker compose ps
docker compose logs --tail=200 app
docker compose restart app
docker compose down
docker compose up -d
```

SSE 流式回答依赖 Caddy 的 `flush_interval -1`，请保留示例反向代理配置。
