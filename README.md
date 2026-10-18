---
id: project-readme
level: L1
summary: Gavin 个人技术博客的公开介绍与当前建设状态
load_when:
  - public-project-overview
author: Gavin
---

# Gavin Blog

Business source for the Gavin blog and question-answering assistant.

- `apps/web/`: Nuxt pages, components, server proxy, and static assets.
- `apps/api/app/`: FastAPI business logic, assistant, index Worker, and E5 service code.
- `apps/api/migrations/`: content database migrations.
- `apps/api/assistant_runtime_migrations/`: assistant runtime database migrations.
- `apps/api/embedding_service/`: separate E5 environment dependency manifest and lockfile.
- `apps/api/scripts/`: contract export, model preparation, provisioning, service entry points, qualification, and backup utilities.
- `packages/contracts/`: OpenAPI contract and generated TypeScript types.

Dependency manifests and lockfiles are committed. Installed dependencies, model weights, real environment files, credentials, databases, and uploaded media are excluded.

Run `npm ci` and `npm run build:web` from the repository root to build the frontend. Python dependencies are managed separately with uv in the API and E5 environment directories.

Ubuntu 22.04 / x86_64 container configuration is provided in [compose.yaml](compose.yaml), with the complete assistant in [compose.assistant.yaml](compose.assistant.yaml). See [deployment instructions](deploy/README.md) for internal E5 TLS, target profile, empty database initialization, model preparation and explicit assistant activation. Production-mode retrieval and real DeepSeek answers were verified in isolated Docker containers; the target server still needs its own configuration and validation. Local data and secrets are excluded from the image build context.

## Harness

Agent 协作入口见 [AGENTS.md](AGENTS.md)，任务路由见 [Harness Index](harness/INDEX.md)。
确定性 CLI 使用 Python 3.11+ 标准库；从 `harness/` 执行 `python -m tools.harness verify` 检查完整性。

Harness 引用的项目文档、业务测试、测试运行脚本和 GitHub Actions 工作流随仓库提供。历史文档中标明的本机原始产物仍留在 Git 外，不能将历史 evidence 当作当前远端的产品验证结果。

从干净检出准备和验证开发环境：

```sh
# 在 apps/api/ 执行
uv sync --locked --extra dev --python 3.11
# 返回仓库根目录执行
npm ci
npx playwright install --with-deps chromium
npm run quality:release
# 单独检查 Harness 完整性（在 harness/ 执行）
python -m tools.harness verify
```

`Release gate / quality-release` 在面向 main 的 pull request、main push 和手动触发时执行发布候选质量链；Harness 结构通过与整站发布候选通过是两项不同的结果。验证范围和生产边界见 [发布准备说明](harness/docs/operations/release-readiness.md)。

为保留归档前的原始 active spec，Git 历史仅从原本地仓库筛选 `harness/` 和 `AGENTS.md` 后接入；筛选后的提交 SHA 会变化。
历史 evidence 内的 source commit 和指纹保持原样，仍表示原始本地验证来源。
