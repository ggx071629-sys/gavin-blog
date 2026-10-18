# 2C/4GiB 复测：并发提问 + 文章增长重建（cloud-test-2c4g）

- 测试时间：2026-09-06（容器 UTC；用户 Asia/Shanghai UTC+8）
- 容器：`cloud-test-2c4g`（2 CPU；4 GiB；无 swap）
- 路径：**Nuxt 生产构建** + 真实 API + 本地 E5 + Qdrant（非 `nuxt dev`）
- OOM 基线：开始时 `oom_kill=0`（全程保持 0，无新 OOM）
- 密钥：未写入本报告

## 最终五问

### 1. 可持续并发用户
| 维度 | 结论 |
|---|---|
| 同 IP | **1**（n=2 时 1 成功 + 1 明确忙线/限流；n≥3 全部 busy） |
| 不同 IP | **3**（n=5/10 恰好 3 路成功，超额得到明确 busy/`concurrency_limited`） |

不同 IP 通过受信头 `X-Gavin-Edge-Client-IP` 注入（应用**不**把 `X-Forwarded-For` 当作计费/限流身份）。

### 2. 已验证内容规模
| 项 | 值 |
|---|---|
| 已发布文章 | **15**（阶梯 3→6→10→15，经后台 API 正常发布的中文运维技术笔记，非 Stage D 评测语料） |
| 正文字节合计 | **11110** |
| 活跃世代 | **22** |
| 活跃 chunk / vector | **82 / 82** |
| `assistant_chunks` 表行数 | 872（含历史世代残留） |
| Qdrant 存储 | ≈ **1.94 GiB**（2082258477 bytes） |

### 3. 重建期间问答是否可用？
- 最大档（15 篇）重建过程中：**不同 IP × 3 并发可用**（3/3 answered）。
- 再抬一档 **×5**：5/5 返回 `assistant_not_ready`。
- 限流有效；重建结束后若门闸 `readiness_drift`，**重启 API（E5 已就绪）** 可恢复并成功问答。
- **无 OOM**；队列可清空。

### 4. 最先出现的瓶颈
**Chat provider 并发上限（=3）+ 同 IP 速率限制**，早于内存耗尽。  
次要：本地 `rebuild/finalize` 与在线 API 门闸交互可能导致 `readiness_drift`。  
内存峰值约 **2.57 GiB / 4 GiB**，生产栈未触顶。

### 5. 相对准则的 Pass/Fail
| 准则 | 结果 |
|---|---|
| 接纳完成；超额明确忙线；无 OOM（Group A） | **PASS** |
| 文章增长阶梯 + 每档重建；最大档重建两次 | **PASS** |
| 最大档重建中提问 | **部分 PASS**（n=3 可用；n=5 变 not_ready） |
| 总评 | **PASS_WITH_LIMITS** |

## Group A — 并发提问

### 同 IP
| n | success | busy | errors | wall_s | OOM |
|---:|---:|---:|---:|---:|---|
| 1 | 1 | 0 | 0 | 2.733 | 否 |
| 2 | 1 | 1 | 0 | 2.508 | 否 |
| 3 | 0 | 3 | 0 | 0.061 | 否 |
| 5 | 0 | 5 | 0 | 0.051 | 否 |
| 10 | 0 | 10 | 0 | 0.083 | 否 |

### 不同 IP（`X-Gavin-Edge-Client-IP`）
| n | success | busy | errors | wall_s | OOM |
|---:|---:|---:|---:|---:|---|
| 1 | 1 | 0 | 0 | 3.159 | 否 |
| 2 | 2 | 0 | 0 | 3.308 | 否 |
| 3 | 3 | 0 | 0 | 2.499 | 否 |
| 5 | 3 | 2 | 0 | 2.920 | 否 |
| 10 | 3 | 7 | 0 | 2.978 | 否 |

## Group B — 文章增长与重建

| 档位 | 文章数 | body bytes | 活跃 chunks | generation | total_s | mem peak | qdrant bytes | failed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 6 | 6 | 8325 | 39 | 16 | 28.4 | 2489352192 | 694053148 | 0 |
| 10 | 10 | 9824 | 61 | 17 | 29.1 | 2529796096 | 925416893 | 0 |
| 15a | 15 | 11110 | 82 | 18 | 32.9 | 2566180864 | 1156804197 | 0 |
| 15b | 15 | 11110 | 82 | 19 | 34.8 | 2574721024 | 1388167835 | 0 |

索引重建使用 `python -m app.local_embedding.local rebuild|finalize`（real-dev 下 API index worker 未启用，admin `/index/rebuilds` 会停在 pending）。

## Group C — 重建中提问（最大档 15 篇）

| 场景 | 结果 |
|---|---|
| 重建中不同 IP ×3 | success=3，可用 |
| 重建中不同 IP ×5 | not_ready=5 |
| 限流 | 有效 |
| 恢复 | finalize 后若门闸 blocked，重启 API 后恢复 answered |
| OOM | 否 |

## 预算（无密钥）

- 日聊天预算上限：2_000_000 micro-CNY（2 CNY）
- 本复测结束 settled ≈ **194400** micro-CNY（约 0.194 CNY）
- 资格探针账本 max_micro_cny=1_000_000（分离）
- 未打满日预算

## 产物

- `/workspace/cloud-test/reports/2c4g-retest-concurrency-rebuild.md`
- `/workspace/cloud-test/reports/2c4g-retest-concurrency-rebuild.json`
- 明细：`/workspace/cloud-test/reports/retest-artifacts/`
