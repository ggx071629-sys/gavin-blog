# Gavin Blog UI 全站视觉审查与改造方案

审查日期：2026-09-05  
文档状态：**Draft / 首轮设计稿已否决并移除；仅保留组件适配结论与审查证据，不存在已批准的改版方向。**  
范围：`apps/web` 的 27 个 Nuxt 页面文件 + `error.vue`，共 28 个页面模板；基线表实际记录 **33 个页面/状态**，不是 29 个。  
视口：1440 × 1000、390 × 844；另对 1024 × 900 导航断点及亮/暗主题代表页面做抽查。  
证据：基线共有 69 张运行态截图；本轮又从当前工作树完成 production build，并在浏览器中连接现有 API 实测首页、长文章、Search 与后台鉴权跳转。缺失内容和已登录后台状态仍引用隔离临时数据库下的基线截图，不把 fixture 状态误写成当前线上数据。

> 边界说明：本次“真实运行”指本机 production-mode Nuxt + 实际 API 的浏览器运行态，不是公网云部署。当前没有用户指定的云平台、域名、凭据或发布授权，因此报告不得使用“已云部署/已上线”的表述。

## 结论

“页面不够高级”只说对了一半。现有视觉并不平庸：归档页、关于页、404、后台登录页和暗色主题已经有清晰个性，编辑器的双栏工作台也很成熟。真正拉低一致性的不是单纯“大字多”，而是：

1. 同一层级存在太多字号系统，公共 H1 上限从 48px 到 72px，首页又是另一套 46.4–70.4px。
2. 大标题与 10–12px 微型元信息之间缺少 13–32px 的稳定中间层级。
3. 多数页面的记忆点只依赖放大标题，内容较少时就变成“大标题 + 大空白 + 小字”。
4. 归档页的编号脊柱、关于页的身份导轨、404 的系统网格是已有的好资产，却没有成为跨页设计语法。
5. 后台整体比公开端稳定，但 Profile、Media、Assistant 三页出现字号漂移、嵌套卡片和过密微型文本。

当前不能根据已否决稿锁定视觉方向。可继续保留 Electric Editorial 基础与下文 R-01 至 R-05 的组件适配判断，但组件组合、布局比例和视觉权重必须在下一轮重新验证。

本报告的 `.run/` 截图为不入库的本机审查产物；路径仅供原审查环境定位，干净检出不包含这些截图。

## 证据口径与本轮真实运行复核

### 可复现环境

| 项目 | 本轮证据 |
|---|---|
| Git revision | `07fee38f2bcf`；工作树非 clean，存在用户进行中的 CSS、首页、ArticleCard 与测试改动，因此这些截图是“当前工作树快照”，不能冒充已提交基线 |
| API | `http://127.0.0.1:8000/api/health` 返回 `{"status":"ok"}` |
| Production build | 在仓库根执行 `npm run build:web`，退出码 0；Nuxt 4.5.1 / Nitro 2.13.4 / Vue 3.5.40 |
| Production runtime | `node .output/server/index.mjs`，浏览器地址 `http://127.0.0.1:3300`，页面无 Nuxt DevTools 注入 |
| Build 风险 | 构建出现大于 500 kB 的客户端 chunk 警告；中文字体文件单个约 1.14–1.59 MB。引入 React 运行时或重型动画库会放大已有性能成本 |

### 浏览器测量，而非仅看代码

| 运行页 | 实测结果 | 截图 |
|---|---|---|
| 首页 / Desktop | 1440 × 1000；H1 为 67.68px / 74.448px；`scrollWidth === clientWidth` | production screenshot（本机产物：`.run/ui-design-review-20260905/runtime/07-home-production-desktop.png`） |
| 首页 / Mobile | 390 × 844；H1 为 46.4px / 51.04px；文档 `scrollWidth 384 - clientWidth 375 = 9px` 横向溢出 | production screenshot（本机产物：`.run/ui-design-review-20260905/runtime/08-home-production-mobile.png`） |
| 长文章 | 页面高度 4586px；正文首个 H2 与 H3 都是 32px / 800 / 38.4px，层级问题在运行态成立 | production screenshot（本机产物：`.run/ui-design-review-20260905/runtime/09-article-production-desktop.png`） |
| Search / Light | placeholder 计算色 `rgb(93 104 138)`、opacity `0.45`，叠加 `rgb(243 245 249)` 后推导对比度约 **1.86:1** | production screenshot（本机产物：`.run/ui-design-review-20260905/runtime/10-search-production-desktop.png`） |
| Search / Dark | placeholder 计算色 `rgb(125 134 164)`、opacity `0.45`，叠加 `rgb(7 8 12)` 后推导对比度约 **1.97:1** | dark screenshot（本机产物：`.run/ui-design-review-20260905/runtime/05-search-desktop-live.png`） |
| `/admin/profile` 未登录访问 | 真实运行会跳转至 `/admin/login?returnTo=/admin/profile`；本轮不伪造登录态，Profile 内页结论来自隔离 fixture 基线 | auth guard screenshot（本机产物：`.run/ui-design-review-20260905/runtime/06-admin-auth-guard-live.png`） |

以上分三类解读：

- **事实**：DOM 计算样式、滚动尺寸、构建结果、路由跳转与截图中可直接观察的状态。
- **专业判断**：层级是否清晰、页面是否过空、哪些既有语言值得跨页复用。
- **待人工验证假设**：哪种设计方向“更高级”、动效是否增强理解、紧凑度是否符合作者气质。三张方向稿只用于验证这些假设。

## 参考站点实查与适配结论

参考文档只提供候选站点，优先级是建议而不是项目约束。项目是 Nuxt/Vue；React Bits、Magic UI 与 shadcn/ui 的示例主要面向 React，因此原则是**借交互与信息结构，不直接把 React 组件塞进 Vue 项目**。任何源码级复用在实现前还要重新核对具体组件许可证、SSR 行为、包体与无障碍状态。

| ID | 实查页面 | 候选用法 | 适配结论 | 运行证据 |
|---|---|---|---|---|
| R-01 | [React Bits / Dot Grid](https://reactbits.dev/backgrounds/dot-grid) | 首页唯一的技术图形或 404 局部网格 | **借鉴，不直装。** 保留点阵密度与局部响应；删掉强紫色、冲击波与全屏持续动画，用 Vue/CSS 或 Canvas 小范围实现，并支持 reduced motion | 截图（本机产物：`.run/ui-design-review-20260905/references/01-react-bits-dot-grid.png`） |
| R-02 | [Magic UI / Blur Fade](https://magicui.design/docs/components/blur-fade) | 页面首载与列表进入 | **可移植为 Vue transition。** 只用于区块首次出现；短时、低位移、无循环，reduced motion 下直接显示 | 截图（本机产物：`.run/ui-design-review-20260905/references/02-magic-ui-blur-fade.png`） |
| R-03 | [Magic UI / Scroll Progress](https://magicui.design/docs/components/scroll-progress) | 4586px 长文章的阅读进度 | **优先采用其模式。** 用原生滚动进度 + CSS transform 即可，不需要引入 React/Motion 依赖；必须与现有 TOC 进度语义合并而非重复 | 截图（本机产物：`.run/ui-design-review-20260905/references/03-magic-ui-scroll-progress.png`） |
| R-04 | [Uiverse / Minimal search input](https://uiverse.io/LightAndy1/tidy-pig-67) | Admin Media 的紧凑过滤器 | **只借分组结构。** 45px 高度可保留；拒绝 12px 圆角、深阴影与 active scale，以匹配 Electric Editorial 的硬边与低装饰语言；公开 Search 不应缩成该小控件 | 截图（本机产物：`.run/ui-design-review-20260905/references/04-uiverse-minimal-search-input.png`） |
| R-05 | [shadcn/ui / Data Table](https://ui.shadcn.com/docs/components/radix/data-table) | AdminResourceList：过滤、列、行操作、分页 | **采用行为模型，Vue 原生实现。** 它是构建指南而非适合直接复制的单一业务表格；避免把 TanStack React 当成必要依赖 | 截图（本机产物：`.run/ui-design-review-20260905/references/05-shadcn-data-table.png`） |
| R-06 | [Anime.js / stagger()](https://animejs.com/documentation/utilities/stagger/) | 编号账本行的顺序进入 | **首轮暂缓。** Anime.js 是动画引擎，不是现成 UI 组件；只有 Vue/CSS 无法满足经过验证的动效目标时再评估依赖 | 截图（本机产物：`.run/ui-design-review-20260905/references/06-animejs-stagger.png`） |

### 问题 → 参考 → 可检验假设

| 当前问题 | 参考模式 | 首轮设计假设 | 验证方式 |
|---|---|---|---|
| 首页记忆点只依赖超大标题 | R-01 Dot Grid + 现有 404 System Grid | 把技术图形限制在一个有边界的区域后，H1 可缩小而不丢辨识度 | 下一轮新方案需同时提供 Desktop/Mobile 对照；不得复用已否决稿作为默认基线 |
| 最近文章卡片高而空 | R-05 的行式信息层级 + 现有 Archive 编号脊柱 | 日期/分类/标题/时长组成账本行，比大卡更快扫读 | 5 秒任务：找到最新文章与阅读时长 |
| 长文章缺少连续反馈 | R-03 Scroll Progress | 一条轻量顶部进度能增强方向感，且不增加正文噪声 | 长文滚动测试、键盘与 reduced-motion 测试 |
| 搜索与媒体检索层级混用 | R-04 的紧凑输入分组 | 公共 Search 保持工作区，后台 Media 使用 44–45px 工具栏，更符合任务密度 | 分别在 idle/loading/results/empty 四态验证 |
| 进入动画可能缺乏节奏 | R-02，必要时再评估 R-06 | 轻量区块进入已足够；无需为“高级感”默认引入动画引擎 | 先做 CSS/Vue 版本，测包体、帧率与 reduced motion |

## 设计决策状态

2026-09-05：首轮三张生成式首页方向稿未达到预期，已由用户否决。项目内稿件及报告链接已移除，后续不得把其布局、虚构遥测或计数当作设计依据。

继续有效的只有本报告中的组件适配判断：R-01 至 R-05 可按限定范围进入后续方案，R-06 暂缓。任何新的视觉方向仍需重新提交可审查证据，并在批准前保持生产 UI 不变。

## 最重要的可见问题

严重度定义：P1 = 影响可读性、无障碍、响应式完整性或关键任务；P2 = 不阻断任务但明显损害层级、一致性或效率。“已有优点”不再冒充 P3 严重度。

### P1：应先修

- 首页移动端出现 9px 横向溢出；长中文标题三行断句失衡。
- 文章正文 H2/H3 同为 32px/800，层级消失；正文行高在文章、项目、读书三套模板间分别约 1.5–1.95。
- Search placeholder 在亮/暗主题的运行态推导对比度分别约 1.86:1 / 1.97:1，远低于普通文本 4.5:1 的目标。
- `/admin/profile` 的页面标题只有 24px，明显小于其他后台页；失败提示引用不存在的 `--ee-danger` token。
- Assistant 中大量状态与事实文本约 10.9–11.5px，视觉和可读性都过弱。

### P2：明显影响高级感

- Articles / Projects / Books 的 Hero 与空状态高度过大，首屏信息密度低。
- 短文章、单项目、单本书时，内容长度没有驱动版式收拢，留下结构性空洞。
- 首页、项目与 404 的大卡面纵向过高，信息靠边、中心空置。
- 中文操作和标签大量使用等宽字体及过宽字距，技术味变成噪声。
- `primary / signal / focus` 在部分主题中几乎同色，语义层次不足。

### 已观察到的优势（不作为严重度）

- 归档页的时间轴、About 的 ID rail、404 的网格舞台辨识度高。
- 文章正文 680–720px 的阅读宽度、代码块和 44px 控件尺寸合理。
- 后台列表、新建页、编辑器、修订页共享语法较稳定。
- 暗色主题的黑底 + signal lime 比亮色主题更有瞬时识别度。

## 逐页审查（每个页面都有本次截图）

| # | 路由 / 状态 | 结论 | 最关键修改 | 桌面 | 移动 |
|---|---|---|---|---|---|
| 01 | `/` | P1 | 首页保留唯一 Display；H1 上限 60px，移动 40–42px；修掉 9px 溢出；最近文章改为紧凑账本行 | 截图（本机产物：`.run/ui-audit-20260904/current/desktop/01-home.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/mobile/01-home.png`） |
| 02 | `/articles` | P2 | H1 从 72px 系统收至 Page 级；筛选与元信息升至 13–14px | 截图（本机产物：`.run/ui-audit-20260904/current/desktop/02-articles.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/mobile/02-articles.png`） |
| 03 | `/notes/**` 长文 | P1 | H2/H3 拆为 30/24px；正文 17/1.8；lede 19px；代码 14px | 截图（本机产物：`.run/ui-audit-20260904/current/desktop/03-article-long.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/mobile/03-article-long.png`） |
| 04 | `/notes/**` 短文 | P1 | 内容短时收紧 Hero、正文与下一篇间距，不按长文保留同样空白 | 截图（本机产物：`.run/ui-audit-20260904/current/desktop/04-article-short.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/mobile/04-article-short.png`） |
| 05 | `/projects` 空 | P2 | 空状态缩短 30–40%；用明确跨链接承接，不造假项目 | 截图（本机产物：`.run/ui-audit-20260904/current/desktop/05-projects-empty.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/mobile/05-projects-empty.png`） |
| 06 | `/projects` 有内容 | P2 | 单项目不再占一张巨大卡；改成 lead row + facts strip | 截图（本机产物：`.run/ui-audit-20260904/current/desktop/05b-projects-populated.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/mobile/05b-projects-populated.png`） |
| 07 | `/projects/:slug` | P2 | 详情 H1 上限 60px；左侧 facts 提升可读性并与正文同节奏 | 截图（本机产物：`.run/ui-audit-20260904/current/desktop/05c-project-detail.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/mobile/05c-project-detail.png`） |
| 08 | `/books` 空 | P2 | 与项目页共用索引壳；空状态缩小，不用大块虚线容器撑满页面 | 截图（本机产物：`.run/ui-audit-20260904/current/desktop/06-books-empty.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/mobile/06-books-empty.png`） |
| 09 | `/books` 有内容 | P2 | 书名、状态、作者建立 24/14/14px 层级；减少上下空洞 | 截图（本机产物：`.run/ui-audit-20260904/current/desktop/06b-books-populated.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/mobile/06b-books-populated.png`） |
| 10 | `/books/**` | P2 | 书封继续做视觉锚点；标题压至 52–60px，元信息升到 13px | 截图（本机产物：`.run/ui-audit-20260904/current/desktop/06c-book-detail.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/mobile/06c-book-detail.png`） |
| 11 | `/archive` | 良好 | 作为公共索引页的基准：年份、编号、蓝线继续保留 | 截图（本机产物：`.run/ui-audit-20260904/current/desktop/07-archive.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/mobile/07-archive.png`） |
| 12 | `/about` | P2 | 保留身份导轨；长句 H1 上限 52px，原则区复用 Section/Subsection | 截图（本机产物：`.run/ui-audit-20260904/current/desktop/08-about.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/mobile/08-about.png`） |
| 13 | `/search` idle | P1 | H1、说明、输入压成紧凑工作区；输入桌面 28–32px | 截图（本机产物：`.run/ui-audit-20260904/current/desktop/09-search-idle.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/mobile/09-search-idle.png`） |
| 14 | `/search` results | P2 | 结果标题与 meta 拉开层级；结果从首屏更早开始 | 截图（本机产物：`.run/ui-audit-20260904/current/desktop/10-search-results.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/mobile/10-search-results.png`） |
| 15 | `/search` empty | P1 | 修 placeholder 对比度；空态保持同骨架，避免纵向跳动 | 截图（本机产物：`.run/ui-audit-20260904/current/desktop/11-search-empty.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/mobile/11-search-empty.png`） |
| 16 | `error.vue` / 404 | P2 | 404 视觉可保留，但恢复动作改为紧凑横向行，避免大而空的行动卡 | 截图（本机产物：`.run/ui-audit-20260904/current/desktop/12-not-found.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/mobile/12-not-found.png`） |
| 17 | `/admin/login` | 良好 | 保留 50/50 舞台；只校正小字与错误态 token | 截图（本机产物：`.run/ui-audit-20260904/current/admin-desktop/13-admin-login.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/admin-mobile/13-admin-login.png`） |
| 18 | `/admin/articles` | P2 | 统一资源列表行高、状态 chip 与行尾操作层级 | 截图（本机产物：`.run/ui-audit-20260904/current/admin-desktop/14-admin-articles.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/admin-mobile/14-admin-articles.png`） |
| 19 | `/admin/articles/new` | P2 | 分为必要信息 / 关联信息 / 正文，减少表单墙 | 截图（本机产物：`.run/ui-audit-20260904/current/admin-desktop/15-admin-articles-new.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/admin-mobile/15-admin-articles-new.png`） |
| 20 | `/admin/articles/:id/edit` | 良好 | 保留 58/42 左右工作台；顶部命令栏更紧凑并粘性定位 | 截图（本机产物：`.run/ui-audit-20260904/current/admin-desktop/16-admin-article-edit.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/admin-mobile/16-admin-article-edit.png`） |
| 21 | `/admin/articles/:id/preview` | P2 | 直接复用公开 Reader；短草稿自动收拢空白 | 截图（本机产物：`.run/ui-audit-20260904/current/admin-desktop/17-admin-article-preview.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/admin-mobile/17-admin-article-preview.png`） |
| 22 | `/admin/articles/:id/revisions` | 良好 | 保留紧凑列表；下一步可升级为时间线 + diff 主从布局 | 截图（本机产物：`.run/ui-audit-20260904/current/admin-desktop/18-admin-article-revisions.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/admin-mobile/18-admin-article-revisions.png`） |
| 23 | `/admin/projects` | P2 | 与文章/读书共用 `AdminResourceList`，减少满屏操作按钮感 | 截图（本机产物：`.run/ui-audit-20260904/current/admin-desktop/19-admin-projects.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/admin-mobile/19-admin-projects.png`） |
| 24 | `/admin/projects/new` | P2 | 复用分段新建表单与底部主动作栏 | 截图（本机产物：`.run/ui-audit-20260904/current/admin-desktop/20-admin-projects-new.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/admin-mobile/20-admin-projects-new.png`） |
| 25 | `/admin/projects/:id/edit` | 良好 | 保留实时预览；校正标题、字段和辅助文字的统一 token | 截图（本机产物：`.run/ui-audit-20260904/current/admin-desktop/21-admin-project-edit.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/admin-mobile/21-admin-project-edit.png`） |
| 26 | `/admin/books` | P2 | 统一资源列表；阅读状态承担语义，操作退到二级 | 截图（本机产物：`.run/ui-audit-20260904/current/admin-desktop/22-admin-books.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/admin-mobile/22-admin-books.png`） |
| 27 | `/admin/books/new` | P2 | 复用分段表单，封面/日期/评分作为一组 | 截图（本机产物：`.run/ui-audit-20260904/current/admin-desktop/23-admin-books-new.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/admin-mobile/23-admin-books-new.png`） |
| 28 | `/admin/books/:id/edit` | 良好 | 复用编辑工作台，预览侧保持粘性并提高正文密度 | 截图（本机产物：`.run/ui-audit-20260904/current/admin-desktop/24-admin-book-edit.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/admin-mobile/24-admin-book-edit.png`） |
| 29 | `/admin/profile` | P1 | H1 统一为后台 30–36px；扁平化媒体区嵌套卡；修错误色 token | 截图（本机产物：`.run/ui-audit-20260904/current/admin-desktop/25-admin-profile.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/admin-mobile/25-admin-profile.png`） |
| 30 | `/admin/taxonomy` | P2 | 统一后台页头；保留对称双列，中文眉题减少字距 | 截图（本机产物：`.run/ui-audit-20260904/current/admin-desktop/26-admin-taxonomy.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/admin-mobile/26-admin-taxonomy.png`） |
| 31 | `/admin/media` | P1 | 上传、检索、资源表只保留两层 surface；强化缩略图与批量工具栏 | 截图（本机产物：`.run/ui-audit-20260904/current/admin-desktop/27-admin-media.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/admin-mobile/27-admin-media.png`） |
| 32 | `/admin/content` | P2 | 拆成“迁移”和“回收站”两项清楚任务；危险动作进入固定危险区 | 截图（本机产物：`.run/ui-audit-20260904/current/admin-desktop/28-admin-content.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/admin-mobile/28-admin-content.png`） |
| 33 | `/admin/assistant` | P1 | 有意义状态不小于 13px；窄屏改为分组/折叠，不强压四列事实 | 截图（本机产物：`.run/ui-audit-20260904/current/admin-desktop/29-admin-assistant.png`） | 截图（本机产物：`.run/ui-audit-20260904/current/admin-mobile/29-admin-assistant.png`） |

注：上表有 33 个“页面/状态”证据行，但仍对应 28 个模板；Search 当前只记录 idle/results/empty 三态。计划中的 `SearchWorkspace` 是 idle/loading/results/empty 四态，**loading 截图仍待补**。

## 统一排版系统

| 语义 Token | 建议值 | 只用于 |
|---|---|---|
| `type.display` | `clamp(40px, 4.25vw, 64px)` / 1.08 / 700 | 仅首页核心陈述 |
| `type.page` | `clamp(36px, 3.25vw, 52px)` / 1.12 / 700 | 公共列表、About、Search 的 H1 |
| `type.detail` | `clamp(40px, 4vw, 60px)` / 1.10 / 700 | 文章、项目、读书详情 H1 |
| `type.ui-title` | `clamp(30px, 2.4vw, 36px)` / 1.15 / 700 | 后台页标题 |
| `type.section` | `clamp(28px, 2.2vw, 32px)` / 1.25 / 700 | H2、区块标题 |
| `type.subsection` | `clamp(20px, 1.8vw, 24px)` / 1.35 / 700 | H3、列表标题 |
| `type.lead` | 19px / 1.65 / 400 | Hero 摘要、正文首段 |
| `type.body` | 17px / 1.80 / 400 | 长文正文 |
| `type.small` | 14px / 1.60 / 400 | 摘要、说明、表单帮助 |
| `type.action` | 14px / 1.25 / 700 | 按钮、导航、可点击文字 |
| `type.label` | 13px / 1.45 / 700 | 日期、分类、状态、面包屑 |
| `type.micro` | 12px / 1.40 / 600 | 仅非关键计数、纯装饰遥测 |
| `type.code` | 14px / 1.70 / 400 | 代码正文与编辑器 |

字体栈建议：

- Sans：`Inter, "Noto Sans SC", system-ui, sans-serif`
- Display：`"Space Grotesk", Inter, "Noto Sans SC", sans-serif`
- Mono：`"JetBrains Mono", "Noto Sans SC", ui-monospace, monospace`

含中文内容优先只使用当前真实载入的 400/700；大量声明 600/800 并不会自动得到可靠的中文字重。中文 label 字距建议约 `0.04em`，`0.08–0.12em` 只留给纯拉丁编号和遥测。

## 模板级改造方案

### 第一阶段：先修系统与缺陷

1. 建立上述 typography tokens，删除各页面局部 H1 尺寸覆盖。
2. 修首页 390px 横向溢出与长标题断句。
3. 修 Search placeholder 对比度，目标至少 4.5:1。
4. `ProfileCard.vue` 的 `--ee-danger` 改为现有 `--ee-danger-ink`。
5. 中文 mono fallback 加入 Noto Sans SC；中文按钮/导航切回 sans。

### 第二阶段：用已有强语言制造记忆点

1. 从 Archive 抽出 **Issue Spine / 年份-编号脊柱**。
2. 从 About 抽出 **Identity Rail / 身份导轨**。
3. 从 404 抽出 **System Grid / 技术网格舞台**，每页最多一处，避免装饰泛滥。
4. 首页只保留一个真实技术图形；列表页用编号账本而非巨大卡片；详情页靠内容、封面、facts 做锚点。

### 第三阶段：按 10 个布局族落地

1. `NarrativeHero`：首页、About。
2. `CollectionIndexShell`：Articles、Projects、Books、Archive。
3. `SearchWorkspace`：Search 四态（idle/loading/results/empty；当前缺 loading 证据）。
4. `EditorialDetailShell`：Article、Project、Book、Admin Preview。
5. `StandaloneStage`：Login、Error。
6. `AdminResourceList`：后台文章/项目/读书列表。
7. `AdminCreateForm`：三个新建页。
8. `EditorWorkspace`：三个编辑页 + Profile。
9. `AdminToolPage`：Taxonomy、Media、Content。
10. `AdminOpsWorkspace`：Revisions、Assistant。

优先完成 2、4、6、8 四族，它们一次覆盖 15 个页面。

### 第四阶段：主题与动效

- 亮色继续以 cobalt 为主，暗色保留 signal lime；拆开 action、signal、focus 三个语义色。
- 过渡只使用 opacity / transform，约 160–220ms；支持 `prefers-reduced-motion`。
- 页面转场不承担信息，Hover 只辅助可点击性，不用持续循环装饰。

## 验收标准

- 公开列表 H1 上限 52px；详情 H1 上限 60px；后台标题统一 30–36px。
- 所有可点击文字不小于 14px；有意义元信息不小于 13px；12px 只做非关键微文案。
- Article H2/H3 分别为 28–32px 与 20–24px；正文 17px / 约 1.8。
- 320、390、640、1024、1280、1440 均无横向溢出；菜单在 639/640/1280 三个临界点行为正确。
- Light/Dark 均通过 axe 与目标 WCAG A/AA 检查；正文/placeholder 文字按适用准则验证对比度，focus 清晰可见。44px 是本项目的触控目标，不冒充 WCAG 2.2 AA 对所有控件的统一硬性尺寸。
- `npm run quality:web` 与 `npm run test:e2e` 通过。
- 改造完成后计划保存 118 张质量矩阵截图进行人工复核；**当前基线是 69 张，不是 118 张**。当前测试只会生成 PNG 和做结构/无障碍断言，没有像素基线比较；“是否更高级”仍必须人工看图。
