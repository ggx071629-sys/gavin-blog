# Ubuntu 22.04 / x86_64 部署准备

本目录为 `linux/amd64` 提供 Docker 构建和启动配置，宿主机沿用已安装的 Nginx。应用镜像使用 Debian Bookworm 基础镜像，与 Ubuntu 宿主机兼容，无需在宿主机额外安装 Node/Python。

默认 `compose.yaml` 启动 Web/API，并关闭问答。完整问答通过 `compose.assistant.yaml` 显式启用，共五个长期容器：Web、API、E5、Qdrant、Worker；宿主机继续使用已有 Nginx。初始化和模型下载是临时任务，不是额外常驻容器。生产模式的真实 Chat、E5 检索、HTTPS/SSE 和引用回答已在隔离 Docker 环境验证，实际服务器的域名、证书、资源及备份配置仍须落实。

## 1. 宿主机准备

使用 [Docker 官方 Ubuntu 安装说明](https://docs.docker.com/engine/install/ubuntu/) 安装 Docker Engine、Buildx 和 Compose 插件；需要 Compose 2.30 或更新版本（使用 raw env_file）。确认：

```bash
uname -m                       # x86_64
docker version                 # Client 和 Server 都可用
docker compose version
```

以下所有 Compose 命令从仓库根目录执行。当前 shell 用户须有 Docker 权限；否则按服务器权限配置使用 sudo。Docker 的访问权限等同于高权限主机访问，不要授予无关账号。

```bash
git clone https://github.com/ggx071629-sys/gavin-blog.git
cd gavin-blog
umask 077
cp .env.example .env
```

编辑 `.env`：把 `SITE_URL` 改为真实的 `https://域名`（不带路径或尾斜杠），填写管理员密码，并分别生成 `PROXY_HMAC_SECRET`、`E5_API_KEY`、`QDRANT_API_KEY`。每个值独立生成，可运行 `openssl rand -hex 32`。禁止使用模板占位值、复用同一个密钥，或把真实值作为镜像构建参数。

可选邮件设置及后续问答参数放在 `.env.assistant`：

```bash
cp deploy/assistant.env.example .env.assistant
chmod 600 .env .env.assistant
```

`.env.assistant` 使用原始值语法，不展开 `${VARIABLE}`；API/Worker 不接收整个根 `.env`，Web 也不接收 Chat/SMTP 密钥。主机文件、证书和秘密不进入 Git 或 Docker 构建上下文。不要公开粘贴 `docker compose config` 或 `docker inspect` 的完整输出，它们可能包含运行秘密；检查语法使用 `docker compose config --quiet`。

## 2. 构建与空库初始化

```bash
docker compose --profile assistant config --quiet
docker compose --profile assistant build --pull web api e5
docker compose run --rm init
docker compose up -d api web
docker compose ps
```

`init` 使用非 root 用户、断网执行完整内容库迁移和独立问答 runtime/checkpoint 初始化；新卷从镜像预置目录继承 UID/GID 10001。它不读取本机旧数据、不调用模型、不自动打开问答。重复初始化不会删表重建数据，但**更新现有实例前必须停止 API/Worker 并备份**。API 启动会检查迁移版本；不要多开 API owner 或复制 API 容器。

仅 Web 暴露 `127.0.0.1:3000`（可用 `WEB_PORT` 改动）。8000/8091/6333/6334 均不映射到公网。浏览器通过同源 `/api/v1` 访问 API，不直接访问内部服务。

## 3. 接入现有 Nginx

把 `deploy/nginx-location.conf` 的内容并入现有域名的 HTTPS `server {}`，替换其旧 `location /`。保留真实域名及已有证书路径；HTTP 入口继续跳转 HTTPS，不要覆盖整台主机的 Nginx 配置。若修改 `WEB_PORT`，同步修改 `proxy_pass`。

```bash
sudo nginx -t
sudo systemctl reload nginx
```

片段保留流式响应、覆盖访客伪造的身份头，Nginx → Nuxt → API 保持同源。API 关闭 Uvicorn 通用代理头改写，保留实际 Nuxt peer，由问答模块验证专用 HMAC 身份。默认桥接网段是 `172.30.71.0/24`，Web 固定 `.10`，网关 `.1`；若与主机/VPN 网络冲突，需一起修改 IPAM、静态地址和双方 trusted proxy CIDR。Ubuntu 上须实测 Nginx 到容器的 peer 是否为网关，不能为省事信任 `0.0.0.0/0`。使用 CDN 时，应先在宿主 Nginx 精确设置 CDN 的可信 real-IP 来源。

通过真实 HTTPS 域名验证阅读、登录、发布、上传与重启持久化。Secure Cookie 在生产开启，直接用 HTTP 端口测试不能证明登录链路成功。

## 4. 配置完整问答

先下载固定 E5 制品，模型以 SHA-256 验证，保存在独立卷，不进镜像或 Git：

```bash
docker compose run --rm model-download
```

下载需要服务器可以访问 Hugging Face。E5 镜像使用独立 CPU Torch 环境，API 镜像只装 tokenizer；生产启动不联网下载模型。E5 以 UID 10001 运行并对卷内 owner lock 加锁，所以模型卷不能整体只读；API/Worker 挂载模型卷为只读。Qdrant 使用固定 `v1.18.3`、API Key 和独立持久卷，不映射主机端口。

以下命令从仓库根目录执行。内部 E5 使用独立自签证书作为明确的信任锚，不需要额外域名或公开证书；此证书与宿主 Nginx 的网站证书不同。证书到期/轮换后须更新 profile 的 CA 摘要、重新探测和签发 readiness，不能关闭证书验证。

```bash
sudo sh deploy/prepare-tls.sh
sudo cp deploy/profile.example.json .deploy/config/profile.json
sudo chown 10001:10001 .deploy/config/profile.json
sudo chmod 640 .deploy/config/profile.json
dc() { docker compose -f compose.yaml -f compose.assistant.yaml --profile assistant "$@"; }
dc config --quiet
```

填写 `.env.assistant` 的模型、密钥、价格、四个独立 HMAC、release ID 和 NTP 设置。DeepSeek 使用 `deepseek-json-object` 输出协议；调用仍由 LangChain 完成，关闭思考与自动重试，JSON 完整解析、引用和 usage 校验都保留。2026-09-13 核验的官方配置为 `https://api.deepseek.com`、`deepseek-flash`、`DeepSeek-V4.1-Flash`，高峰输入/输出分别为 2/8 元每百万 tokens；上线当日必须重新核对 [官方价格](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/)，不能沿用旧版模型身份。价格模板故意留空/零值，不代表模型免费。

`profile.example.json` 是**未批准、不可直接启动的填写模板**。用实际事实填写域名、镜像/软件版本与 SHA-256、CA 摘要、服务器磁盘与资源、备份及观测约定，再填写批准信息。现有生产 profile 的资源门槛仍为 **2 vCPU / 4096 MiB**，服务器不同不能假填相同数字，需要先调整并验证相应资源合同。模板中的空值/false 不是通过的证明。

profile 的关键绑定值须和运行设置一致：路径 `/data/content/gavin.db`、`/data/content/write.lock`、`/data/runtime/assistant.db`、`/data/media`、`/qdrant/storage`；Qdrant 为 `172.30.71.40:6333`；E5 为 `https://172.30.71.30:8091/v1`，batch/concurrency 1、384 维、384/64 分块。CA 文件是 `/run/assistant/e5-ca.crt`；`model_lock_sha256` 对应源码 `apps/api/app/local_embedding/model.lock.json`。模板已固定模型制品摘要。实际 profile 和 probe 只存 `.deploy/`，不进 Git。

先保持根 `.env` 的 `ASSISTANT_API_ENABLED=false`、`ASSISTANT_UI_ENABLED=false`。验证 profile，记录输出的 digest 到 `.env.assistant` 的 `GAVIN_ASSISTANT_QUALIFICATION_PROFILE_DIGEST`：

```bash
dc stop api worker
dc run --rm --no-deps api python scripts/assistant_qualification.py validate /run/assistant/profile.json
dc up -d e5 qdrant
dc ps
```

必须等 E5 healthy 后进行真实探测。探测的费用和次数由 profile 的 `qualification_max_micro_cny`、`qualification_max_calls` 限制，包含失败调用；批准总额与运行每日预算是不同配置，禁止通过新建账本重置已使用的授权。保留所有历史探测输出。以下命令会调用真实 Chat，须先确定本次 envelope：

```bash
dc run --rm --no-deps -e GAVIN_ASSISTANT_INDEX_WORKER_ENABLED=false api \
  python scripts/run_assistant_provider_qualification.py \
  --profile /run/assistant/profile.json \
  --approve-profile-digest 'sha256:填写上一步得到的摘要' \
  --ledger /evidence/provider-ledger.json --output /evidence/provider-probe.json \
  --chat --embedding
```

确认 Chat 与 Embedding 都是 pass，再计算 `.deploy/evidence/provider-probe.json` 的 SHA-256，将带 `sha256:` 前缀的值填入 `GAVIN_ASSISTANT_PROVIDER_PROBE_SHA256`。DeepSeek 的证明为 `application_schema=true`、`strict_schema=false`，这准确表示应用严格校验 JSON，而非宣称供应商原生 strict JSON Schema。

如需先发布内容，可在 API 开关仍为 false 时运行 `dc up -d api web`，通过博客管理端发布需要供问答检索的内容，再运行 `dc stop api worker` 后执行首次重建。空库可以启动，但没有公开内容时助手会返回证据不足，不能凭空回答站点内容。

```bash
dc run --rm --no-deps worker python -m app.assistant_index.worker --rebuild
dc run --rm --no-deps api python /opt/deploy/assistant-control.py --list-rebuilds
```

确认 operation 状态为 `ready_to_switch`，记录其 `id` 和 `version`。将根 `.env` 的 `ASSISTANT_API_ENABLED=true`，在 API/Worker 均停止时执行 owner 切换及 readiness：

```bash
dc run --rm --no-deps api python /opt/deploy/assistant-control.py \
  --probe /evidence/provider-probe.json --operation '填写operation-id' --version 1
```

`--version` 必须使用上一步实际值，不固定为 1。工具使用独占 runtime owner 锁，不调用 Chat，也不自动打开运营开关。再次签发现有 generation 的 readiness 可省略 operation/version。所有 `dc run api/worker` 前须停止对应常驻容器，避免 owner 或固定 IP 冲突。

最后设置 `ASSISTANT_UI_ENABLED=true`，启动服务，在管理端核对 readiness、索引、预算后显式启用问答：

```bash
dc up -d api web worker
dc ps
```

经真实网站 HTTPS 检查会话、带引用回答、SSE、真实访客 IP、异常请求拒绝及预算扣减，再完成服务器备份恢复/资源验收。切换 generation 或配置漂移会关闭有效准入，需要重新验证和签发 readiness。API/Worker 获得 CA 公钥，只有 E5 挂载内部 TLS 私钥，Web 不获得 Chat Key。

## 5. 数据、更新与恢复

长期数据保存在项目命名的 Docker volumes：`content`（内容库与共同写锁）、`media`（上传文件）、`runtime`（短会话/账本）、`models`（模型）、`vectors` 和 `vector-snapshots`（Qdrant）。Worker **没有 runtime 卷**。`docker compose down` 保留数据；不要使用 `down -v`，它会删除这些卷。

备份必须形成内容库和媒体的共同一致恢复点，并加密保存到主机外；沿用后端 backup helper 或停写后一起备份。不要直接复制运行中的 SQLite 主文件而漏掉 WAL。runtime 不进入长期备份，Qdrant 是可重建派生数据。模型可重新下载。

更新前保存旧镜像标签和备份；先拉取确定提交、设置新 `IMAGE_TAG` 并构建，再停止写入、迁移和启动：

```bash
docker compose stop web api worker
docker compose run --rm init
docker compose up -d api web
```

此处省略了必须完成的共同备份操作，不能把三条命令当作完整更新流程。数据库迁移不保证可逆，应用回滚不能代替数据库恢复。基础 Node/Python 镜像固定主版本/发行版、应用依赖使用锁文件；正式发布应记录构建产物 digest，回滚使用保留的镜像，不临时重建旧代码。

已经启用问答的实例，更新时使用第 4 节的 `dc`（始终带问答 overlay）执行 stop/run/up，并同步新的 artifact、release/profile 绑定和 readiness；不要用基础 `docker compose up` 覆盖已有问答配置。

## 验证状态

2026-09-13 在 Docker Desktop 的 Linux/amd64 引擎（29.7.2、Compose 5.5.1）上完成以下验证，使用独立项目、全新卷、临时凭据和自签测试证书：

- Web、API、E5 三个镜像真实构建成功，依赖在 Linux 镜像内按锁文件安装。
- Compose 全 profile 解析成功；仅 Web 映射 loopback，Worker 无 runtime 卷，问答两个开关保持关闭。
- 断网初始化完整内容库和 runtime/checkpoint，两次执行均成功；API 在 UID 10001 和只读根文件系统下健康运行。
- 临时 Nginx 配置校验、HTTPS 页面、同源 API、HSTS、Secure Cookie 登录及 session 查询通过。
- 创建合成草稿后重新创建 API 容器，内容和管理员登录仍正常。
- 固定 E5 制品下载及 SHA-256 校验成功；真实推理返回归一化的 384 维向量；E5/Qdrant 鉴权通过且匿名请求被拒绝。
- 问答 overlay 在 `production` 模式下运行 E5 HTTPS、真实 Worker 重建、API owner finalize、真实 provider probe 和 readiness，随后通过管理员接口启用。
- 同源 HTTPS/SSE 返回中文答案及指向合成已发布文章的引用。此前缺少浏览器 Fetch Metadata 的请求被 403 拒绝，补齐正常浏览器头后通过。
- 两次真实 Chat 总计 1984 输入 tokens、87 输出 tokens；按高峰价格保守计费为 4664 micro-CNY，即 **0.004664 元**，低于本次 2 元授权。E5 无外部供应商费用。
- 测试环境和原始账本保持本地，正式配置模板中不包含本次临时凭据或测试数据。
- 本次相关自动回归共 117 项通过，包含 provider/profile、E5、在线问答、runtime 完整性与 prompt 预算检查。

没有迁移本机业务数据。上述 profile 使用明确标记的隔离集成测试 fixture，证明代码链路可用，不是用户服务器的批准 profile。Docker Desktop 的 Linux 测试不能替代 Ubuntu 服务器上的真实域名、Nginx 真实 IP、资源和恢复验收。

### 2 核 / 4GB 资源演练

本次交付候选的 142 项相关回归通过，覆盖生产 provider/profile、E5、在线问答、runtime 完整性、prompt 预算及引用格式；Compose 三层合并配置与内部证书脚本语法检查通过。迁移检查首次因运行目录错误失败，在候选的 `apps/api/` 目录重新执行后通过。本轮未追加真实模型调用、Ubuntu 实机或长期负载测试。

在完成问答配置后，可将资源 overlay 放在最后；后续初始化、重建和运行始终使用同一组文件：

```bash
dc() { docker compose -f compose.yaml -f compose.assistant.yaml -f compose.resources.yaml --profile assistant "$@"; }
```

2026-09-13 本地 WSL2 / Docker 演练让全部应用和测试 Nginx 共用 CPU 0、1，容器禁止 swap。Web/API/Worker/E5/Qdrant 的内存上限分别为 256/768/640/1536/256 MiB，应用合计 3456 MiB，按 4 GiB 主机留出 640 MiB 给系统、Docker 和宿主 Nginx。该余量需要在真实主机核实。

- 20 篇合成文章的索引重建耗时 21.6 秒。初始 Worker 384 MiB、API 512 MiB 均发生过 OOM；这些失败没有隐藏。
- 修复在线 API 重复构造 E5 分词器的问题，以及 SSE 在终态提交与通知竞态下漏发最后事件的问题。
- 最终 3 个独立用户同时提问全部返回带引用的答案，耗时 6.894/7.087/7.805 秒；最终容器重启次数与 OOM kill 均为 0。
- 最终阶段每约 4 秒采样，应用加测试 Nginx 的同时内存占用采样峰值约 2390 MiB；这不包含宿主系统，也不能覆盖采样间瞬时峰值。E5 历史 cgroup 峰值触及 1536 MiB 上限，仍需监控内存余量。
- 资源修复相关回归 47 项通过；扩展回归曾发现引用编号错误分类问题，随后已修复并单独提交。引用修复的 44 项相关回归通过。另一个提示词文本断言在修改前版本也失败，未纳入本次修复，不能宣称全套测试通过。
- 本任务累计 9 次有实际 usage 的 Chat 调用，保守账本累计 0.027518 元，低于累计 2 元授权。临时容器已停止，秘密、合成数据和详细账本留在本地。

结论是当前小数据量、3 用户并发的应用链路可以在该资源分配内运行。尚未完成完整 Ubuntu 22.04 的 4GB 虚拟机测试、长时间负载、索引重建与在线提问同时运行，以及 70GB 实际磁盘配额测试。共享两个本机逻辑 CPU 不能保证与云服务器两个 vCPU 同速。模型卷约 471 MiB，70GB 还需容纳系统、镜像、构建缓存、媒体和备份；此 overlay 不限制构建期资源。上线前仍需目标服务器验收。
