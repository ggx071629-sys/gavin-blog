# 2C/4GiB 盲测稳定性报告（cloud-test-2c4g）

- 测试时间：2026-09-06（容器 UTC；用户 Asia/Shanghai UTC+8）
- 容器：cloud-test-2c4g（Ubuntu 22.04；2 CPU；4 GiB；无 swap）
- 项目：/workspace/app/my_blog
- 结论一句话：**必须优化或升级配置**

## 环境

| 项 | 实测 |
|---|---|
| memory.max | 4294967296 |
| cpu.max | 200000 100000 |
| Node | v22.19.0 |
| Python/uv | 3.11.15 / 0.12.10 |
| Qdrant | 1.15.5 musl（1.18.3 gnu 需 GLIBC_2.38） |
| E5 | multilingual-e5-small ~471MiB 已加载 |
| Chat | configured（密钥不入库） |

## 1 能否启动？

- 依赖安装：根目录包安装通过（峰值约 1.57 GiB）；API/embedding uv sync 通过；安装无 OOM。
- E5+Qdrant：健康；embeddings dim=384；合计约 1.84 GiB。
- 索引 rebuild/finalize generation=14 通过（rebuild 峰值约 2.33 GiB）；Chat probe 通过（834 micro-CNY）。
- 默认真实入口（Nuxt 开发服务器 + real API）：docker stats 达 3.999 GiB；cgroup oom_kill=1；dmesg 杀死 node（anon-rss≈2.15GiB）；docker OOMKilled=true；web 退出 137。**默认入口启动失败。**
- 缓解：nuxt 生产构建后稳态约 2.05–2.17 GiB，可继续测，不等于默认入口合格。

## 2 是否流畅？（生产 Web 路径）

- 首页约 51–65ms；文章约 29–38ms；api health 约 2ms。
- 真实问答：SSL 配置题 answered 1.761s；DeepSeek/Codex 题 answered 3.710s；重建中提问 answered 1.444s。
- 宽泛题 insufficient_evidence 约 0.9–1.3s（管线完整）。

## 3 负载？

- 双并发提问 wall 3.69s，两路均 answer；内存约 2.11 GiB；无 OOM。
- 曾触发 rate_limited（产品限流）；chat concurrency=1。
- rebuild 同时浏览：generation 15 成功；首页持续 200；峰值约 2.55 GiB；同期提问成功。

## 4 长跑与重启？

- 浸泡约 10 分钟 / 20 样本：home p50/p95 0.063/0.080s；全 200；mem 约 3135–3147 MiB 平稳；无新 OOM。
- 重启须先 E5 就绪再启 API；乱序则 embed 连接失败。有序重启后提问 1.714s answered；稳态约 2.68 GiB。

## 内存峰值摘要（docker stats）

| 阶段 | 峰值 MiB |
|---|---|
| 包安装 | 1610.8 |
| E5+Qdrant | 2004.0 |
| 索引 rebuild | 2385.9 |
| Nuxt-dev OOM | 4095.0 |
| 生产稳态 | 2625.5 |

cgroup memory.peak=4295012352；oom_kill=1。

## 最终结论

### 必须优化或升级配置

1. 默认真实问答开发栈在 2C/4GiB 必然 OOM，与阶段 D 7–8 GiB 规划一致。
2. 生产构建可勉强跑通浏览/问答/轻负载/10 分钟浸泡，但头寸薄、重启顺序敏感。
3. 建议升级至至少 8 GiB，或强制生产 Web、分进程、维护错峰、systemd 保证 E5→API。

不可宣称 2C/4GiB 可直接使用默认真实入口。

## 产物

- /workspace/cloud-test/reports/2c4g-blind-test-report.md
- /workspace/cloud-test/reports/2c4g-blind-test-summary.json
- 容器 cloud-test-2c4g 仍存在；应用进程已停止

