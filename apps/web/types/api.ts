export type ContentType = 'article' | 'project' | 'book'

export type AssistantFactStatus = 'healthy' | 'degraded' | 'blocked' | 'disabled' | 'stale' | 'unknown'
export type AssistantOperationStatus = 'pending' | 'running' | 'waiting' | 'catch_up' | 'ready_to_switch' | 'switch_pending' | 'switched' | 'failed' | 'abandoned'

export interface AssistantObservedFact {
  status: AssistantFactStatus
  reason_code: string
  observed_at: string | null
  freshness_seconds: number | null
  stale: boolean
}

export interface AssistantAvailability {
  requested_state: 'disabled' | 'enabled'
  effective_state: 'disabled' | 'enabled' | 'blocked'
  version: number
  operational_epoch: number
  blocked_reason: string | null
  switch_pending_operation_id: string | null
  switch_target_generation_id: number | null
  updated_at: string | null
  draining_attempts: number
}

export interface AssistantBudget {
  kind: 'chat' | 'query_embedding' | 'index_embedding'
  beijing_date: string
  cap_micro_cny: number | null
  settled_micro_cny: number | null
  reserved_micro_cny: number | null
  remaining_micro_cny: number | null
  overage_micro_cny: number | null
  circuit_open: boolean | null
  calls: number | null
  input_tokens: number | null
  output_tokens: number | null
  usage_known: boolean
  observed_at: string | null
  authority: 'runtime' | 'content'
}

export interface AssistantOperation {
  operation_id: string
  kind: 'rebuild'
  status: AssistantOperationStatus
  version: number
  generation_id: number | null
  previous_generation_id: number | null
  source_cursor: string | null
  outbox_high_water: number | null
  safe_error_code: string | null
  message: string | null
  created_at: string
  updated_at: string
  terminal_at: string | null
}

export interface AssistantAdminSnapshot {
  status: 'complete' | 'partial'
  observed_at: string
  runtime_observed_at: string | null
  content_observed_at: string
  deployment: { api_capability: boolean; single_api_owner: boolean; launcher_source: 'web_runtime_config'; launcher_mounted: null }
  availability: AssistantAvailability
  readiness: AssistantObservedFact
  cleanup: AssistantObservedFact
  restore: AssistantObservedFact
  qdrant: AssistantObservedFact
  chat_provider: AssistantObservedFact
  embedding_provider: AssistantObservedFact
  worker: AssistantObservedFact
  manifest: { generation_id: number | null; provider: string | null; model: string | null; model_version: string | null; dimension: number | null; pipeline_version: string | null; collection_present: boolean | null }
  queue: { pending: number; leased: number; succeeded: number; failed: number; latest_success_at: string | null }
  operation: AssistantOperation | null
  budgets: AssistantBudget[]
  daily_activity: { accepted_questions: number | null; rate_limit_decisions: number | null; refusals: number | null; errors: number | null; security_events: number | null; latency_ms_min: number | null; latency_ms_max: number | null; feedback_helpful?: number | null; feedback_unhelpful?: number | null; stages?: { stage: string; count: number; latency_ms_min: number | null; latency_ms_max: number | null }[] }
}

export interface AssistantIndexTask {
  id: number
  source_type: 'article' | 'project' | 'book' | 'profile' | 'about' | 'resume'
  source_id: number
  target_version: string
  pipeline_version: string
  operation: 'upsert' | 'delete' | 'purge'
  status: 'pending' | 'leased' | 'succeeded' | 'failed'
  version: number
  attempt_count: number
  safe_error_code: string | null
  message: string | null
  parent_task_id: number | null
  operator_authorized: boolean
  created_at: string
  updated_at: string
}

export interface AssistantIndexTaskList { items: AssistantIndexTask[]; limit: number; offset: number }

export interface TaxonomyItem {
  id: number
  name: string
  slug: string
  description: string
}

export interface TaxonomyOption {
  id: number
  name: string
  slug: string
  article_count: number
}

export interface PublicTaxonomy {
  categories: TaxonomyOption[]
  tags: TaxonomyOption[]
  total_article_count: number
}

export interface ArticleReference {
  kind: 'external' | 'internal'
  display_title: string
  url: string | null
  target_type: ContentType | null
  target_id: number | null
}

export interface WikiResolution {
  token: string
  display_title: string
  public_path: string | null
  content_type: ContentType | null
}

export interface PublicBacklink {
  content_type: ContentType
  id: number
  title: string
  summary: string
  published_at: string
  public_path: string
}

export interface Article {
  id: number
  title: string
  slug: string
  summary: string
  published_at: string | null
  content: string
  status: 'draft' | 'published'
  version: number
  current_revision_id: number | null
  current_publish_revision: number | null
  has_unpublished_changes: boolean
  created_at: string
  updated_at: string
  deleted_at: string | null
  public_path: string | null
  category: TaxonomyItem | null
  tags: TaxonomyItem[]
  references: ArticleReference[]
  wikilinks: WikiResolution[]
}

export interface PublicArticle {
  id: number
  title: string
  slug: string
  summary: string
  content: string
  published_at: string
  updated_at: string
  public_path: string
  category: TaxonomyItem | null
  tags: TaxonomyItem[]
  references: PublicReference[]
  wikilinks: WikiResolution[]
}

export interface ArticleContext {
  previous: RelatedArticle | null
  next: RelatedArticle | null
  related: RelatedArticle[]
  backlinks: PublicBacklink[]
}

export interface PublicReference {
  display_title: string
  url: string
}

export interface Project {
  id: number
  title: string
  slug: string
  summary: string
  content: string
  repository_url: string | null
  website_url: string | null
  status: 'draft' | 'published'
  version: number
  current_revision_id: number | null
  current_publish_revision: number | null
  has_unpublished_changes: boolean
  published_at: string | null
  created_at: string
  updated_at: string
  deleted_at: string | null
  public_path: string | null
  article_ids: number[]
}

export interface RelatedArticle {
  id: number
  title: string
  slug: string
  summary: string
  published_at: string
  public_path: string
}

export interface PublicProject {
  id: number
  title: string
  slug: string
  summary: string
  content: string
  repository_url: string | null
  website_url: string | null
  published_at: string
  updated_at: string
  public_path: string
  related_articles: RelatedArticle[]
  backlinks: PublicBacklink[]
  wikilinks: WikiResolution[]
}

export type ReadingStatus = 'planned' | 'reading' | 'completed' | 'paused'

export interface BookNote {
  id: number
  book_title: string
  author: string
  slug: string
  cover_url: string | null
  reading_status: ReadingStatus
  reading_date: string | null
  rating: number | null
  summary: string
  content: string
  status: 'draft' | 'published'
  version: number
  current_revision_id: number | null
  current_publish_revision: number | null
  has_unpublished_changes: boolean
  published_at: string | null
  created_at: string
  updated_at: string
  deleted_at: string | null
  public_path: string | null
}

export interface PublicBookNote {
  id: number
  book_title: string
  author: string
  slug: string
  cover_url: string | null
  reading_status: ReadingStatus
  reading_date: string | null
  rating: number | null
  summary: string
  content: string
  published_at: string
  updated_at: string
  public_path: string
  backlinks: PublicBacklink[]
  wikilinks: WikiResolution[]
}

export interface SearchResult {
  content_type: ContentType
  content_id: number
  title: string
  summary: string
  snippet: string
  public_path: string
  published_at: string
  score: number
}

export interface MediaVariant {
  format: string
  mime_type: string
  url: string
  byte_size: number
  width: number
  height: number
}

export interface MediaAsset {
  id: number
  source: 'upload' | 'external'
  original_name: string
  alt_text: string
  mime_type: string
  width: number | null
  height: number | null
  byte_size: number | null
  url: string
  variants: MediaVariant[]
  created_at: string
  deleted_at: string | null
}

export interface LifecycleBatchItemResult {
  id: number
  ok: boolean
  error_code: string | null
  error_message: string | null
}

export interface LifecycleBatchResponse {
  results: LifecycleBatchItemResult[]
}

export interface TrashItem {
  content_type: ContentType
  content_id: number
  title: string
  slug: string
  status: 'draft' | 'published'
  deleted_at: string
}

export interface MarkdownImportItem {
  filename: string
  content_type: ContentType
  content_id: number
  slug: string
  warnings: string[]
}

export interface MarkdownImportResponse {
  imported: MarkdownImportItem[]
}

export interface ProfilePublic {
  name: string
  title: string
  bio: string
  skills: string[]
  avatar_url?: string
  github_url?: string
  website_url?: string
  resume_url?: string
  city?: string
  email?: string
}

export interface Profile {
  id: number
  name: string
  title: string
  bio: string
  skills: string[]
  avatar_url: string | null
  city: string | null
  city_visible: boolean
  github_url: string | null
  website_url: string | null
  email: string | null
  email_visible: boolean
  resume_url: string | null
  version: number
  created_at: string
  updated_at: string
}

export interface ProfileUpdate {
  name: string
  title: string
  bio: string
  skills: string[]
  avatar_url: string | null
  city: string | null
  city_visible: boolean
  github_url: string | null
  website_url: string | null
  email: string | null
  email_visible: boolean
  resume_url: string | null
  version: number
}

export type AboutNowStatus = 'in_progress' | 'building' | 'exploring'
export type AboutNowTarget = 'projects' | 'articles' | 'books'

export interface AboutCapability {
  title: string
  description: string
  tags: string[]
}

export interface AboutNowItem {
  label: string
  status: AboutNowStatus
  target: AboutNowTarget
}

export interface AboutSiteStackItem {
  label: string
  value: string
}

export interface AboutSite {
  description: string
  stack: AboutSiteStackItem[]
}

export interface AboutPageContent {
  statement: string
  capabilities: AboutCapability[]
  now: AboutNowItem[]
  editorial_topics: string[]
  site: AboutSite
}

export interface AboutPageAdmin {
  id: number
  content: AboutPageContent
  status: 'draft' | 'published'
  version: number
  current_revision_id: number | null
  current_publish_revision: number | null
  has_unpublished_changes: boolean
  published_at: string | null
  created_at: string
  updated_at: string
}

export interface AboutRevisionSummary {
  id: number
  revision_number: number
  source: 'editor' | 'rollback'
  published_at: string
  content_sha256: string
  rollback_from_revision_id: number | null
}

export interface AboutRevisionDetail extends AboutRevisionSummary {
  content: AboutPageContent
}

export interface AboutRevisionDiffResponse {
  from_revision_id: number
  to_revision_id: number
  statement: string
  capabilities: string
  now: string
  editorial_topics: string
  site: string
}

export interface ArticleRevisionSummary {
  id: number
  revision_number: number
  title: string
  slug: string
  source: 'editor' | 'incubator' | 'rollback'
  published_at: string
  content_sha256: string
  rollback_from_revision_id: number | null
}

export interface ArticleRevisionDetail {
  id: number
  article_id: number
  revision_number: number
  title: string
  slug: string
  summary: string
  content: string
  category: TaxonomyItem | null
  tags: TaxonomyItem[]
  references: PublicReference[]
  source: 'editor' | 'incubator' | 'rollback'
  published_at: string
  first_published_at: string
  content_sha256: string
  rollback_from_revision_id: number | null
}

export interface ArticleRevisionDiffResponse {
  article_id: number
  from_revision_id: number
  to_revision_id: number
  title: string
  summary: string
  content: string
  category: string
  tags: string
  references: string
}

export interface AssistantClientPolicy {
  question_max_chars: number
  session_idle_seconds: number
  session_absolute_seconds: number
  body_retention_seconds: number
}

export interface AssistantCitation {
  n: string
  alias?: string | null
  title: string
  heading_path?: string | null
  path: string
}

export interface AssistantSource {
  n: string
  title: string
  heading_path?: string | null
  path: string
}

export interface AssistantSessionTurn {
  turn_id: string
  created_at: string
  status: string | null
  code: string | null
  message: string | null
  question: string | null
  answer: string | null
  citations: AssistantCitation[] | null
  sources: AssistantSource[] | null
  body_available: boolean
  feedback?: 'helpful' | 'unhelpful' | null
}

export interface AssistantActiveTurn {
  turn_id: string
  question: string | null
  created_at: string
  stage: 'checking' | 'retrieving' | 'composing' | 'validating' | null
}

export interface AssistantSessionCreateResponse {
  session_id: string
  csrf_token: string
  idle_expires_at: string
  absolute_expires_at: string
  policy: AssistantClientPolicy
}

export interface AssistantSessionStatusResponse {
  session_id: string
  created_at: string
  idle_expires_at: string
  absolute_expires_at: string
  policy: AssistantClientPolicy
  turns: AssistantSessionTurn[]
  active_turn: AssistantActiveTurn | null
}

export interface AssistantErrorEnvelope {
  error: { code: string, message: string }
}

/** Counts follow the search term; total also follows the selected status. */
export interface AdminListQuery<T> {
  items: T[]
  total: number
  counts: { all: number; published: number; draft: number }
}
