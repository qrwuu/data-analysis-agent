# Security Policy / 安全策略

## Responsible disclosure / 漏洞报告

请通过 GitHub 仓库的 **Security → Report a vulnerability** 提交私密漏洞报告。报告中请包含影响范围、复现步骤、必要的日志或截图，以及建议的缓解方式。请勿在公开 Issue 中发布密钥、真实业务数据或可直接利用的攻击细节。

Please use **Security → Report a vulnerability** in the GitHub repository for private disclosure. Include the impact, reproduction steps, relevant logs or screenshots, and suggested mitigations. Do not publish credentials, real business data, or directly exploitable details in a public issue.

## Security baseline / 安全基线

- Secrets are loaded from local configuration or environment variables and are excluded from version control.
- SQL requests pass AST-level read-only validation before execution.
- Sensitive workspace paths such as `.env`, `.ssh`, `.git`, and private keys are blocked.
- Browser responses use CSP, same-origin write protection, content-type protection, and restrictive permissions headers.
- Uploaded files, session data, generated artifacts, and logs stay in the configured runtime directory.

安全问题会在确认后按影响范围进行修复，并通过仓库安全公告或版本说明披露。
