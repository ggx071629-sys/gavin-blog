<template>
  <section class="assistant-management">
    <header class="am-header">
      <div><h1>问答助手管理</h1></div>
      <div class="am-tools"><span v-if="snapshot">更新于 {{ time(snapshot.observed_at) }}</span><button :disabled="loading" @click="refresh"><StudioIcon name="refresh" />{{ loading ? '刷新中…' : '刷新状态' }}</button><NuxtLink :to="viewLink('maintenance')">高级维护</NuxtLink></div>
    </header>
    <nav class="am-tabs" aria-label="助手管理视图"><NuxtLink :to="viewLink('overview')" :aria-current="view === 'overview' ? 'page' : undefined">概览</NuxtLink><NuxtLink :to="viewLink('test')" :aria-current="view === 'test' ? 'page' : undefined">试问</NuxtLink></nav>
    <p v-if="error && !panelOpen" class="am-alert" role="alert">{{ error }}</p>
    <p v-if="success && !panelOpen" class="am-hint" role="status">{{ success }}</p>
    <p v-if="stale && snapshot" class="am-alert" role="status">上次成功读取于 {{ time(snapshot.observed_at) }}，以下事实可能已过期。请刷新状态。</p>
    <p v-if="!snapshot" class="am-loading" role="status">{{ loading ? '正在读取助手状态…' : '暂时无法读取助手状态' }}</p>
    <template v-if="snapshot">
      <div v-show="view !== 'test'">
        <section class="am-availability" aria-labelledby="service-status">
          <div class="am-availability-copy"><h2 id="service-status"><span class="am-dot" :data-open="headline === '已向访客开放'" />{{ headline }}</h2><p>{{ statusExplanation }}</p></div>
          <div class="am-actions"><NuxtLink v-if="isOpen" class="button-primary" :to="viewLink('test')">试问助手</NuxtLink><button :class="isOpen ? 'am-link' : 'button-primary'" :disabled="mutating || (!isOpen && (stale || !canEnable))" @click="confirmAvailability">{{ isOpen ? '关闭对外问答' : '向访客开放' }}</button><NuxtLink v-if="!isOpen" class="am-link" :to="viewLink('test')">试问助手</NuxtLink></div>
        </section>
        <section class="am-attention" aria-labelledby="attention-heading"><h2 id="attention-heading">需要处理</h2>
          <div v-if="issues.length" class="am-issues"><div v-for="issue in issues" :key="issue.title" class="am-issue"><StudioIcon name="alert-circle-filled" /><div><h3>{{ issue.title }}</h3><p>{{ issue.body }}</p><button v-if="issue.action === 'budget'" class="am-link" @click="openBudget">修改预算 →</button><button v-else-if="issue.action === 'sync'" class="am-link" @click="showSync = true; filter = 'failed'">查看失败内容 →</button><NuxtLink v-else class="am-link" :to="viewLink('maintenance')">查看处理说明 →</NuxtLink></div></div></div>
          <p v-else class="am-clear">暂无待处理事项</p>
        </section>
        <section class="am-row" aria-labelledby="cost-heading">
          <div><h2 id="cost-heading">今日费用</h2><p>北京时间每日 00:00 重置</p></div>
          <div v-if="management"><p class="am-amount">{{ money(management.usage_known ? budget?.settled_micro_cny : null) }} <span>/ {{ money(budget?.cap_micro_cny) }}</span></p><progress v-if="management.usage_known && !stale" :value="occupied" :max="Math.max(1, budget?.cap_micro_cny || 0)" aria-label="今日预算占用" /><p v-else class="am-budget-unknown" role="status">预算占用暂不可确认</p><p>进行中预留 {{ money(management.usage_known ? budget?.reserved_micro_cny : null) }}</p></div>
          <div class="am-row-actions"><button class="am-link" aria-label="修改预算" :disabled="!budget || stale" @click="openBudget">修改预算 ↗</button><button class="am-link" :aria-expanded="showCosts" @click="showCosts = !showCosts">费用明细 {{ showCosts ? '−' : '+' }}</button></div>
        </section>
        <section class="am-row am-knowledge" aria-labelledby="sync-heading"><div><h2 id="sync-heading">知识同步</h2><p>发布与更新后自动同步公开内容</p></div><div><h3>{{ syncSummary }}</h3><p>{{ snapshot.queue.latest_success_at ? `最近完成 ${time(snapshot.queue.latest_success_at)}` : '尚无成功同步记录' }}</p></div><div class="am-row-actions"><button class="am-link" :aria-expanded="showSync" @click="showSync = !showSync">查看内容 {{ showSync ? '−' : '↗' }}</button></div></section>
        <section class="am-row" aria-labelledby="feedback-heading">
          <div><h2 id="feedback-heading">短会话反馈</h2><p>仅统计未到期回答的赞踩，清除后删除；不能当作正确率。</p></div>
          <div><p>有帮助 {{ stale ? '待刷新' : snapshot.daily_activity.feedback_helpful ?? '未确认' }} · 没有帮助 {{ stale ? '待刷新' : snapshot.daily_activity.feedback_unhelpful ?? '未确认' }}</p><p>今日回答耗时 {{ stale ? '待刷新' : `${snapshot.daily_activity.latency_ms_min ?? '未确认'}–${snapshot.daily_activity.latency_ms_max ?? '未确认'} ms` }}</p></div>
          <details><summary>今日阶段耗时</summary><p v-for="item in snapshot.daily_activity.stages || []" :key="item.stage">{{ stageName[item.stage] || item.stage }}：{{ item.count }} 次，{{ item.latency_ms_min ?? '未确认' }}–{{ item.latency_ms_max ?? '未确认' }} ms</p><p>范围内最小/最大耗时，不是生产百分位。诊断事件保留 7 天，不含正文。</p></details>
        </section>

      </div>
      <AssistantAdminTrial v-if="trialVisited" v-show="view === 'test'" :available="!!management?.trial_available && !stale" :public-closed="!isOpen" @settled="load" />

    </template>
    <AdminDialog v-model="panelOpen" :labelledby="panelTitleId" :close-disabled="mutating" :width-class="['sync', 'maintenance'].includes(panel) ? 'am-dialog-wide' : ''">
      <div v-if="snapshot" ref="panelRoot" class="am-dialog-content">
        <div class="am-dialog-toolbar"><button aria-label="关闭弹窗" :disabled="mutating" @click="closePanel"><StudioIcon name="x" /></button></div>
        <p v-if="error" class="am-alert" role="alert">{{ error }}</p>
        <p v-if="success" class="am-hint" role="status">{{ success }}</p>
        <p v-if="stale" class="am-alert" role="status">状态可能已过期，请关闭弹窗并刷新状态。</p>
        <div v-if="panel === 'costs'" class="am-details"><h2 id="costs-title" tabindex="-1">今日费用明细</h2><div v-for="item in snapshot.budgets" :key="item.kind" class="am-detail-row"><strong>{{ budgetLabel[item.kind] }}</strong><span>已用 {{ money(management?.usage_known && !stale ? item.settled_micro_cny : null) }}</span><span>预留 {{ money(management?.usage_known && !stale ? item.reserved_micro_cny : null) }}</span></div><div v-for="item in management?.scope_costs.filter(item => item.scope !== 'index')" :key="item.scope + item.kind" class="am-detail-row"><span>{{ item.scope === 'admin' ? '后台试问' : '访客问答' }} · {{ budgetLabel[item.kind] }}</span><span>{{ money(management?.usage_known && !stale ? item.settled_micro_cny : null) }}</span></div><p>按部署价格计量，不代表供应商最终账单。总预算与原有分类授权上限同时生效。</p></div>
        <section v-if="panel === 'sync'" class="am-sync" aria-label="内容同步记录">
          <div class="am-section-heading"><h2 id="sync-title" tabindex="-1">内容同步记录</h2><div class="am-filter"><label for="sync-filter">状态</label><select id="sync-filter" v-model="filter" @change="offset = 0"><option value="">全部</option><option value="pending">待同步</option><option value="leased">同步中</option><option value="failed">失败</option><option value="succeeded">已处理</option></select></div></div>
          <p>每行是一项同步任务。历史任务成功不代表当前公开修订已收录。已被当前索引覆盖的历史失败不计入待处理；旧调用费用仍需单独核对。</p>
          <div v-for="task in tasks?.items" :key="task.id" class="am-task"><div><strong>{{ task.title }}</strong><p>{{ typeLabel[task.source_type] }} · {{ time(task.updated_at) }}</p><p v-if="task.message"><template v-if="task.resolved_by_current_index">历史错误：</template>{{ task.message }}</p></div><span>{{ syncLabel(task) }}</span><button v-if="canRetry(task)" class="am-link" :disabled="mutating" @click="retry(task)">重试此内容同步</button><NuxtLink v-else-if="task.status === 'failed' && !task.resolved_by_current_index" class="am-link" :to="viewLink('maintenance')">查看诊断</NuxtLink><span v-else /></div>
          <p v-if="!tasks?.items.length" class="am-hint">当前筛选下暂无同步任务。</p><div class="am-pagination"><button :disabled="!offset || loading" @click="offset = Math.max(0, offset - 10)">上一页</button><span>{{ tasks?.total ? offset + 1 : 0 }}–{{ Math.min(offset + 10, tasks?.total || 0) }} / {{ tasks?.total || 0 }}</span><button :disabled="offset + 10 >= (tasks?.total || 0) || loading" @click="offset += 10">下一页</button></div>
        </section>
        <section v-if="panel === 'maintenance'" class="am-maintenance" aria-labelledby="maintenance-heading">
        <h2 id="maintenance-heading" tabindex="-1">高级维护</h2><p>刷新只读取已有运行事实，不发起付费探测。</p>
        <div class="am-maintenance-row"><div><h3>运行资格</h3><p>切换索引后，先校验当前索引并签发资格，再恢复试问与对外开放。校验不产生模型调用费用。</p><p v-if="!management?.trial_stopped || isOpen" class="am-hint">请先停止全部问答，再执行校验。</p></div><button class="button-secondary" :disabled="mutating || stale || !management?.trial_stopped || isOpen || !snapshot.manifest.generation_id || !!snapshot.availability.switch_pending_operation_id" @click="renewReadiness">{{ renewingReadiness ? '正在校验…' : '校验并签发资格' }}</button></div>
        <div class="am-maintenance-row"><div><h3>后台试问</h3><p>{{ management?.trial_stopped ? '全部问答已被停止。运行条件验证通过后，可单独恢复后台试问。' : '普通对外关闭不影响试问；资格与维护保护仍然生效。' }}</p></div><button v-if="management?.trial_stopped" class="button-secondary" :disabled="mutating || stale || snapshot.readiness.status !== 'healthy'" @click="resumeTrial">恢复后台试问</button><NuxtLink v-else class="am-link" :to="viewLink('test')">前往试问</NuxtLink></div>
        <div class="am-maintenance-row"><div><h3>索引维护</h3><p>重建使用今日总预算，旧索引继续提供回答。切换后全部问答暂停，需要重新验证运行资格。</p><p v-if="snapshot.operation" class="assistant-operation">当前操作：{{ operationLabel(snapshot.operation.status) }}</p></div><div class="am-row-actions"><button class="button-secondary" :disabled="mutating || nonterminalOperation" @click="confirmRebuild">重建公开知识索引</button><button v-if="snapshot.operation?.status === 'ready_to_switch'" class="button-primary" :disabled="mutating" @click="confirmFinalize">切换到新索引</button></div></div>
        <div class="am-maintenance-row"><div><h3>紧急停止全部问答</h3><p>同时撤销访客和管理员执行，已发送的调用仍可能产生费用。</p></div><button class="am-danger" :disabled="mutating" @click="confirmEmergency">紧急停止全部问答</button></div>
        <h3 class="am-diagnostics-title">运行诊断</h3><div v-for="fact in facts" :key="fact.label" class="am-diagnostic"><strong>{{ fact.label }}</strong><span>{{ assistantFactLabel[fact.fact.status] }}{{ fact.fact.stale ? '（观察已过期）' : '' }}</span><code>{{ fact.fact.reason_code }}</code></div>
        <dl class="am-technical"><div><dt>部署能力</dt><dd>{{ snapshot.deployment.api_capability ? '允许 API 运行' : 'API 未开启' }} · {{ launcherConfigured ? '访客入口配置允许' : '访客入口配置未开启' }}</dd></div><div><dt>索引版本</dt><dd>{{ snapshot.manifest.generation_id ?? '未知' }} · {{ snapshot.manifest.model || '模型未知' }}</dd></div></dl>
        <details class="am-runbook"><summary>如何处理运行条件问题</summary><p>切换索引后：点击“校验并签发资格”，通过后分别恢复后台试问和对外开放。首次部署、密钥或运行配置变更仍需在服务器完成部署资格验证。</p><p>同步进程不可用：检查索引 Worker 进程和最近错误，恢复进程后刷新；发布与撤回仍以内容库事实为准。</p><p>调用结果未知：先核对供应商账单与后台尝试记录，避免直接重发造成重复费用。删除和撤回不等待付费预算。</p><p>数据恢复期间：等待北京时间下一日的恢复保护窗口结束，再验证索引与运行配置。</p></details>
      </section>
        <form v-if="panel === 'budget'" class="am-budget-form" @submit.prevent="saveBudget"><h2 id="budget-title" tabindex="-1">修改每日预算</h2><p>北京时间每日 00:00 重置。设为 0 暂停新增付费调用。</p><label for="daily-budget">每日总预算（元）</label><input id="daily-budget" v-model="budgetInput" inputmode="decimal" autocomplete="off" autofocus><p>当前已用 {{ money(management?.usage_known && !stale ? budget?.settled_micro_cny : null) }}，预留 {{ money(management?.usage_known && !stale ? budget?.reserved_micro_cny : null) }}。部署允许上限 {{ money(budget?.ceiling_micro_cny) }}。</p><p>每日上限从 {{ money(budget?.cap_micro_cny) }} 调整为 {{ money(amountToMicro(budgetInput)) }}。</p><p v-if="budgetError" class="am-alert" role="alert">{{ budgetError }}</p><div class="am-actions"><button type="button" class="button-secondary" :disabled="mutating" @click="budgetOpen = false">取消</button><button class="button-primary" :disabled="mutating">{{ mutating ? '保存中…' : '保存预算' }}</button></div></form>
        <div v-if="panel === 'confirm'" class="am-budget-form"><h2 id="confirm-title" tabindex="-1">{{ confirmation.title }}</h2><p>{{ confirmation.body }}</p><div class="am-actions"><button class="button-secondary" :disabled="mutating" @click="confirmOpen = false">取消</button><button :class="confirmation.danger ? 'am-danger' : 'button-primary'" :disabled="mutating" @click="runConfirmed">{{ confirmation.title }}</button></div></div>
      </div>
    </AdminDialog>
  </section>
</template>

<script setup lang="ts">
import '~/assets/css/assistant-management.css'
import type { AssistantObservedFact } from '~/types/api'
import { assistantFactLabel, assistantOperationIsTerminal } from '~/utils/assistant-admin'
import { amountToMicro, budgetLabel, canRetry, money, serviceHeadline, syncLabel, type SyncTask } from '~/utils/assistant-management'
import { isAssistantUiEnabled } from '~/utils/assistant/flag'

definePageMeta({ layout: 'admin-core', middleware: 'admin' })
useSeoMeta({ title: '问答助手管理' })
const route = useRoute()
const view = computed(() => ['test', 'maintenance'].includes(String(route.query.view)) ? String(route.query.view) : 'overview')
const viewLink = (next: string) => ({ path: '/admin/assistant', query: next === 'overview' ? {} : { view: next } })
const trialVisited = ref(view.value === 'test')
watch(view, value => { if (value === 'test') trialVisited.value = true })
const launcherConfigured = isAssistantUiEnabled(useRuntimeConfig().public.assistantUiEnabled)
const { snapshot, management, tasks, loading, mutating, stale, error, success, filter, offset, load, refresh, mutate } = useAssistantManagement()
const budget = computed(() => management.value?.budget)
const isOpen = computed(() => snapshot.value?.availability.requested_state === 'enabled')
const canEnable = computed(() => snapshot.value?.deployment.api_capability && snapshot.value.readiness.status === 'healthy' && snapshot.value.cleanup.status === 'healthy' && snapshot.value.restore.status === 'healthy')
const headline = computed(() => snapshot.value ? serviceHeadline(snapshot.value, management.value, stale.value) : '')
const statusExplanation = computed(() => stale.value ? '请先刷新状态，再决定是否开放。' : !launcherConfigured ? '访客入口尚未在部署配置中开启，请查看高级维护。' : !isOpen.value ? '访客入口已隐藏，符合运行条件时仍可在后台试问。' : '访客入口与新问题由此开关统一控制，入口最多 30 秒更新。')
const occupied = computed(() => (budget.value?.settled_micro_cny || 0) + (budget.value?.reserved_micro_cny || 0))
const showCosts = ref(false)
const showSync = ref(false)
watch(showCosts, open => { if (open) showSync.value = false })
watch(showSync, open => { if (open) showCosts.value = false })
watch(view, () => { showCosts.value = false; showSync.value = false })
const syncSummary = computed(() => {
  const queue = snapshot.value?.queue
  if (!queue) return '同步状态待确认'
  if (queue.failed) return `${queue.failed} 项同步失败`
  if (queue.pending || queue.leased) return `${queue.pending + queue.leased} 项待同步`
  return '暂无待同步任务'
})
const issues = computed(() => {
  const value = snapshot.value
  if (!value) return []
  const list: { title: string, body: string, action: string }[] = []
  if (value.daily_activity.errors) list.push({ title: `今日 ${value.daily_activity.errors} 次回答失败`, body: '这是本机已观察的失败计数，请结合阶段原因与费用核查；不会自动重试或向外部发送告警。', action: 'maintenance' })
  if (value.queue.failed) list.push({ title: `${value.queue.failed} 项内容同步失败`, body: '回答可能缺少这些内容。可安全重试的任务提供单独操作。', action: 'sync' })
  if (budget.value && budget.value.remaining_micro_cny < budget.value.question_headroom_micro_cny) list.push({ title: '剩余预算不足以开始一次问答', body: '内容同步暂缓。可在授权上限内调整预算，或等待北京时间次日恢复。', action: 'budget' })
  if (!value.deployment.api_capability || value.readiness.status !== 'healthy' || value.cleanup.status === 'blocked' || value.restore.status === 'blocked') list.push({ title: '当前运行条件需要处理', body: '查看诊断中的资格、维护锁和部署状态，处理后刷新。', action: 'maintenance' })
  if (value.worker.status !== 'healthy' || value.worker.stale) list.push({ title: '内容同步状态待确认', body: '同步进程不可用或观察已过期，新发布内容可能尚未进入助手。', action: 'maintenance' })
  return list
})
const time = (input: string) => new Intl.DateTimeFormat('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Shanghai' }).format(new Date(/Z$|[+-]\d\d:\d\d$/.test(input) ? input : `${input}Z`))
const stageName: Record<string, string> = { checking: '问题检查', retrieving: '检索', evidence_gate: '证据检查', composing: '生成', validating: '输出校验' }
const typeLabel: Record<string, string> = { article: '文章', project: '项目', book: '书评', profile: '个人资料', about: '关于页', resume: '简历' }
const operationLabel = (status: string) => ({ pending: '排队中', running: '重建中', waiting: '等待预算', catch_up: '同步增量', ready_to_switch: '等待切换', switch_pending: '切换中', switched: '已切换', failed: '失败', abandoned: '已取消' })[status] || status
const nonterminalOperation = computed(() => !!snapshot.value?.operation && !assistantOperationIsTerminal(snapshot.value.operation.status))
const facts = computed<{ label: string, fact: AssistantObservedFact }[]>(() => snapshot.value ? [
  { label: '运行资格', fact: snapshot.value.readiness }, { label: '清理保护', fact: snapshot.value.cleanup }, { label: '恢复保护', fact: snapshot.value.restore }, { label: '向量索引', fact: snapshot.value.qdrant }, { label: '回答服务', fact: snapshot.value.chat_provider }, { label: '检索服务', fact: snapshot.value.embedding_provider }, { label: '同步进程', fact: snapshot.value.worker },
] : [])
const key = (scope: string) => `${scope}-${crypto.randomUUID()}`
const retry = (task: SyncTask) => mutate(() => apiFetch(`/admin/assistant/index/tasks/${task.id}/retry`, { method: 'POST', body: { expected_status: 'failed', expected_version: task.version, operator_authorized: false }, headers: { 'Idempotency-Key': key('retry') } }), '已提交此内容同步重试。')
const renewingReadiness = ref(false)
const renewReadiness = async () => {
  const current = snapshot.value
  if (!current?.manifest.generation_id || mutating.value) return
  renewingReadiness.value = true
  try {
    await mutate(() => apiFetch('/admin/assistant/readiness/renew', {
      method: 'POST', body: { expected_generation_id: current.manifest.generation_id, expected_version: current.availability.version },
    }), '运行资格已通过校验，可分别恢复后台试问和对外开放。')
  }
  finally { renewingReadiness.value = false }
}
const resumeTrial = () => mutate(() => apiFetch('/admin/assistant/trial/resume', { method: 'POST' }), '后台试问已恢复，对外开放状态未改变。')
const confirmOpen = ref(false)
const confirmation = ref({ title: '', body: '', danger: false })
let action: () => Promise<unknown> = async () => {}
const confirmAction = (title: string, body: string, callback: () => Promise<unknown>, danger = false) => { confirmation.value = { title, body, danger }; action = callback; confirmOpen.value = true }
const confirmAvailability = () => {
  const enabled = !isOpen.value
  confirmAction(enabled ? '向访客开放' : '关闭对外问答', enabled ? '开放后访客可以提问，费用计入今日预算。' : '关闭后拒绝访客新问题并隐藏入口；已发送调用可能仍产生费用，后台试问不受影响。', () => apiFetch('/admin/assistant/availability', { method: 'PATCH', body: { enabled, expected_version: snapshot.value!.availability.version } }))
}
const confirmRebuild = () => confirmAction('重建公开知识索引', '重建将使用今日总预算。新索引准备完成后，需要手动切换并重新验证资格。', () => apiFetch('/admin/assistant/index/rebuilds', { method: 'POST', body: {}, headers: { 'Idempotency-Key': key('rebuild') } }))
const confirmFinalize = () => { const operation = snapshot.value?.operation; if (operation) confirmAction('切换到新索引', '切换会暂停全部问答。重新验证运行资格后，需分别恢复试问和对外开放。', () => apiFetch(`/admin/assistant/index/rebuilds/${operation.operation_id}/finalize`, { method: 'POST', body: { expected_version: operation.version }, headers: { 'Idempotency-Key': key('finalize') } })) }
const confirmEmergency = () => confirmAction('紧急停止全部问答', '访客与管理员执行将同时撤销。已发送调用仍可能结算费用。', () => apiFetch('/admin/assistant/emergency-stop', { method: 'POST' }), true)
const runConfirmed = async () => { if (await mutate(action, `${confirmation.value.title}：操作已完成。`)) confirmOpen.value = false }
const budgetOpen = ref(false)
const budgetInput = ref('')
const budgetError = ref('')
let budgetVersion = 0
const openBudget = () => { if (!budget.value) return; budgetInput.value = String(budget.value.cap_micro_cny / 1000000); budgetVersion = budget.value.version; budgetError.value = ''; budgetOpen.value = true }
const saveBudget = async () => {
  const amount = amountToMicro(budgetInput.value)
  if (amount === null) { budgetError.value = '请输入非负金额，最多六位小数。'; return }
  if (amount > (budget.value?.ceiling_micro_cny || 0)) { budgetError.value = '金额超过部署授权上限。'; return }
  const ok = await mutate(() => apiFetch('/admin/assistant/budget', { method: 'PATCH', body: { cap_micro_cny: amount, expected_version: budgetVersion } }), '每日总预算已保存。')
  if (ok) budgetOpen.value = false
  else { budgetError.value = '保存未完成。输入已保留，请核对刷新后的上限再保存。'; await load(); budgetVersion = budget.value?.version || 0 }
}
const router = useRouter()
const panelReady = ref(false)
onMounted(() => { panelReady.value = true })
const panel = computed(() => !panelReady.value || !snapshot.value ? '' : confirmOpen.value ? 'confirm' : budgetOpen.value ? 'budget' : view.value === 'maintenance' ? 'maintenance' : showCosts.value ? 'costs' : showSync.value ? 'sync' : '')
const panelTitleId = computed(() => ({ '': '', confirm: 'confirm-title', budget: 'budget-title', maintenance: 'maintenance-heading', costs: 'costs-title', sync: 'sync-title' })[panel.value] || '')
const closePanel = () => {
  if (mutating.value) return
  if (confirmOpen.value) confirmOpen.value = false
  else if (budgetOpen.value) budgetOpen.value = false
  else if (view.value === 'maintenance') void router.push(viewLink('overview'))
  else { showCosts.value = false; showSync.value = false }
}
const panelOpen = computed({ get: () => !!panel.value, set: open => { if (!open) closePanel() } })
const panelRoot = ref<HTMLElement | null>(null)
watch(panel, async (next, previous) => {
  if (next && previous) {
    await nextTick()
    const target = panelRoot.value?.querySelector<HTMLElement>('[autofocus], h2')
    target?.focus()
  }
})
watch(mutating, async busy => {
  if (!busy && panel.value) {
    await nextTick()
    if (!panelRoot.value?.contains(document.activeElement)) panelRoot.value?.querySelector<HTMLElement>('h2')?.focus()
  }
})
</script>
