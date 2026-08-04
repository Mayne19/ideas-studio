export type User = {
  id: string
  username: string | null
  name: string
  first_name: string | null
  last_name: string | null
  email: string
  avatar_url: string | null
  is_active: boolean
  is_staff: boolean
  created_at: string
  updated_at: string
}

export type Project = {
  id: string
  owner_id: string | null
  name: string
  domain: string | null
  locale: string
  timezone: string
  audience: string | null
  tone: string | null
  reader_level: string | null
  writing_style: string | null
  vertical: string | null
  word_count_min: number | null
  word_count_max: number | null
  status: ProjectStatusCode
  public_tracking_key_prefix: string | null
  connected_at: string | null
  last_seen_at: string | null
  public_site_url: string | null
  revalidate_url: string | null
  revalidate_configured: boolean
  last_revalidated_at: string | null
  last_revalidate_status: string | null
  last_revalidate_error: string | null
  created_at: string
  updated_at: string
}

export type ProjectRole = 'owner' | 'admin' | 'editor' | 'designer' | 'viewer'

export type ActivityLog = {
  id: string
  project_id: string
  user_id: string | null
  user_name: string | null
  action: string
  resource_type: string | null
  resource_id: string | null
  description: string | null
  metadata: Record<string, unknown> | null
  created_at: string
}

export type ProjectMember = {
  user_id: string
  user_name: string | null
  user_email: string | null
  user_username: string | null
  role: ProjectRole
  status: string
  created_at: string
}

export type ConnectInfo = {
  project_id: string
  domain: string | null
  status: ProjectStatusCode
  public_tracking_key: string | null
  secret_api_key_masked: string | null
  connected_at: string | null
  last_seen_at: string | null
  snippet: string
  public_api_endpoints: Record<string, string>
  public_site_url: string | null
  revalidate_url: string | null
  revalidate_secret: string | null
  revalidate_configured: boolean
  last_revalidated_at: string | null
  last_revalidate_status: string | null
  last_revalidate_error: string | null
}

export type LoginResponse = {
  access_token: string
  token_type: string
}

// Statuts d'article : voir frontend/src/lib/status.ts pour les codes/labels/
// couleurs (backend renvoie désormais un entier, plus une chaîne).
export type { ArticleStatusCode, ProjectStatusCode } from '@/lib/status'
import type { ArticleStatusCode, ProjectStatusCode } from '@/lib/status'

export type Article = {
  id: string
  project_id: string
  category_id: string | null
  sub_niche: string | null
  title: string
  slug: string
  content: string | null
  excerpt: string | null
  status: ArticleStatusCode
  keyword: string | null
  meta_title: string | null
  meta_description: string | null
  word_count: number
  priority: number
  is_featured: boolean
  seo_score: number | null
  readability_score: number | null
  quality_score: number | null
  eeat_score: number | null
  geo_score: number | null
  global_score: number | null
  global_score_valid: boolean | null
  is_validable: boolean | null
  validation_reasons: string[]
  critical_warnings: Array<{ type: string; severity: string; message: string }>
  published_at: string | null
  scheduled_for: string | null
  created_at: string
  updated_at: string
  author_name: string | null
  reading_time_minutes: number | null
  target_word_count: number | null
  content_format: 'short' | 'medium' | 'long' | 'pillar' | null
  angle: string | null
  search_intent: string | null
  opportunity_score: number | null
  audience: string | null
  rejection_reason: string | null
  rejection_note: string | null
  has_draft_changes: boolean
}

export type IdeaGenerateRequest = {
  context_hint?: string | null
  preferred_title?: string | null
  keyword?: string | null
  category_id?: string | null
  audience?: string | null
  angle?: string | null
  search_intent?: string | null
  include_faq?: boolean | null
  include_callouts?: boolean | null
}

export type IdeaGenerateResponse = {
  id: string
  title: string
  keyword: string | null
  category_id?: string | null
  search_intent: string | null
  opportunity_score: number | null
  status: ArticleStatusCode
  provider_name?: string | null
  model_name?: string | null
}

export type IdeaRejectRequest = {
  rejection_reason?: string | null
  rejection_note?: string | null
}

export type IdeaPriorityRequest = {
  priority: number
}

export type IdeaLaunchRequest = {
  mode: 'idea_only' | 'full_article'
  dry_run?: boolean
  context_hint?: string | null
  preferred_title?: string | null
  keyword?: string | null
  category_id?: string | null
  audience?: string | null
  angle?: string | null
  search_intent?: string | null
  include_faq?: boolean | null
  include_callouts?: boolean | null
}

export type IdeaLaunchResponse = {
  project_id: string
  mode: string
  dry_run: boolean
  ideas_generated: number
  article_ids: string[]
  provider_name?: string | null
  model_name?: string | null
}

export type BulkDeleteResponse = {
  deleted: number
  skipped: number
  deleted_ids: string[]
  skipped_items: Array<{ id: string; reason: string }>
  message: string
}

export type Category = {
  id: string
  project_id: string
  name: string
  slug: string
  description: string | null
  color: string | null
  priority_score: number | null
  monthly_target: number | null
  is_pipeline_enabled: boolean
  editorial_goal: string | null
  target_audience: string | null
  internal_notes: string | null
  word_count_min: number | null
  word_count_max: number | null
  created_at: string
  updated_at: string
}

export type CalloutTemplate = {
  id: string
  project_id: string
  slug: string
  label: string
  style: string | null
  default_title: string | null
  color_background: string | null
  color_border: string | null
  color_text: string | null
  icon: string | null
  source: 'imported' | 'manual' | string
  external_id: string | null
  class_name: string | null
  created_at: string
}

export type SeoIssue = {
  type: string
  category: 'seo' | 'readability' | 'quality' | 'eeat'
  severity: 'info' | 'warning' | 'critical'
  message: string
  suggestion: string
  section: string | null
  auto_fix_available: boolean
}

export type AnalysisBrief = {
  seo_score: number | null
  readability_score: number | null
  quality_score: number | null
  eeat_score: number | null
  geo_score: number | null
  global_score: number | null
  created_at: string
}

export type SeoAnalysis = {
  id: string
  article_id: string
  project_id: string
  seo_score: number
  readability_score: number
  quality_score: number
  eeat_score: number
  readiness_status: string
  issues: SeoIssue[]
  suggestions: string[]
  created_at: string
}

export type SeoExpertIssue = {
  check: string
  severity: 'info' | 'warning' | 'critical' | string
  message: string
}

export type SeoExpertReview = {
  score_global: number
  seo_score: number
  eeat_score: number
  readability_score: number
  issues: SeoExpertIssue[]
  recommendations: string[]
  passed_checks: string[]
  failed_checks: string[]
  knowledge_pack_sources?: {
    google?: Array<{ name: string; url: string; role: string }>
    eeat?: string
    content_quality?: string
    humanization?: string
    review_rules?: string
  }
  diagnostics?: {
    word_count?: number
    first_h2?: string
    faq_count?: number
    average_sentence_length?: number
  }
}

export type ReadyCheck = {
  article_id: string
  readiness_status: string
  seo_score: number
  readability_score: number
  quality_score: number
  eeat_score: number
  global_score: number | null
  global_score_valid: boolean | null
  blocking_issues: SeoIssue[]
  critical_warnings: Array<{ type: string; severity: string; message: string }>
  can_publish: boolean
}

export type ArticleVersion = {
  id: string
  article_id: string
  project_id: string
  title: string
  revision_no: number
  source: 'ai' | 'human' | 'import' | 'rollback' | string
  created_by: string | null
  created_at: string
}

// Sortie de tous les agents (project_context, outline, eeat_checklist, ...)
// indexée par agent_key — remplace les ~30 colonnes *_json de l'ancien modèle,
// voir ai.artifacts côté backend (app/services/seo/artifacts.py).
export type ArtifactsMap = Record<string, Record<string, unknown>>

export type EditorArticle = {
  id: string
  project_id: string
  category_id: string | null
  sub_niche: string | null
  title: string
  slug: string
  content: string | null
  excerpt: string | null
  status: ArticleStatusCode
  keyword: string | null
  meta_title: string | null
  meta_description: string | null
  faq: Array<{ question: string; answer: string }>
  callouts: unknown[]
  word_count: number
  artifacts: ArtifactsMap
  author_name: string | null
  reading_time_minutes: number | null
  is_featured: boolean
  latest_analysis: AnalysisBrief | null
  created_at: string
  updated_at: string
  published_title: string | null
  published_content: string | null
  published_excerpt: string | null
  published_meta_description: string | null
  has_draft_changes: boolean
}

export type AutosaveRequest = {
  title?: string | null
  slug?: string | null
  content?: string | null
  excerpt?: string | null
  keyword?: string | null
  meta_title?: string | null
  meta_description?: string | null
  faq?: Array<{ question: string; answer: string }> | null
  callouts?: unknown[] | null
  category_id?: string | null
  sub_niche?: string | null
  author_name?: string | null
  is_featured?: boolean | null
}

export type AutosaveResponse = {
  id: string
  word_count: number
  updated: boolean
  version_created: boolean
  updated_at: string
}

export type PreviewResponse = {
  id: string
  title: string
  slug: string
  content: string | null
  excerpt: string | null
  meta_title: string | null
  meta_description: string | null
  sub_niche: string | null
  is_featured: boolean
  faq: Array<{ question: string; answer: string }>
  callouts: unknown[]
  author_name: string | null
  reading_time_minutes: number | null
  status: ArticleStatusCode
}

export type ApiValidationError = {
  loc: (string | number)[]
  msg: string
  type: string
}

export type ApiErrorDetail = string | ApiValidationError[]

// ── Performance ────────────────────────────────────────────────────────────

export type TrafficTrendPoint = {
  date: string
  views: number
}

export type TopPage = {
  path: string
  views: number
}

export type TrafficReferrer = {
  referrer: string
  views: number
}

export type TrafficCountry = {
  country: string
  views: number
}

export type TrafficDevice = {
  device: string
  views: number
}

export type PerformanceSummary = {
  tracking_status: 'not_configured' | 'configured_no_data' | 'connected_with_data' | 'error'
  total_views: number
  unique_pages: number
  top_pages: TopPage[]
  referrers: TrafficReferrer[]
  countries: TrafficCountry[]
  devices: TrafficDevice[]
  trend_by_day: TrafficTrendPoint[]
  channel_trend_by_day: {
    date: string
    direct: number
    organic: number
    social: number
    referral: number
  }[]
  period: string
}

export type ArticlePerformance = {
  article_id: string
  views: number
  referrers: TrafficReferrer[]
  countries: TrafficCountry[]
  daily_views: TrafficTrendPoint[]
  last_seen_at: string | null
  period: string
}

export type ArticlePerformanceBrief = {
  article_id: string
  title: string
  slug: string
  views: number
  variation: number | null
  seo_score: number | null
  published_at: string | null
}

// ── Recommendations ────────────────────────────────────────────────────────

export type RecommendationStatus = 'pending' | 'accepted' | 'rejected' | 'applied'

export type RecommendationType =
  | 'improve_title'
  | 'improve_meta_description'
  | 'add_faq'
  | 'add_internal_links'
  | 'refresh_content'
  | 'improve_intro'
  | 'improve_eeat'
  | 'expand_section'
  | 'fix_low_traffic'
  | 'update_keywords'

export type OptimizationRecommendation = {
  id: string
  project_id: string
  article_id: string | null
  type: RecommendationType | string
  priority: number
  reason: string
  suggestion: string
  status: RecommendationStatus | string
  created_at: string
  resolved_at: string | null
}

export type Invitation = {
  id: string
  project_id: string
  email: string
  role: string
  token: string | null
  invited_by_user_id: string | null
  target_user_id: string | null
  accepted_at: string | null
  expires_at: string
  created_at: string
}

export type InvitationCreateResult = Invitation

export type InvitationInfo = {
  project_name: string
  role: string
  email: string
  expires_at: string
  already_accepted: boolean
  expired: boolean
}

export type Notification = {
  id: string
  project_id: string
  user_id: string | null
  type: string
  title: string
  message: string
  level: string
  link: string | null
  read_at: string | null
  created_at: string
}

// ── AI Agents ─────────────────────────────────────────────────────────────

export type AgentInfo = {
  agent_id: string
  name: string
  description: string
  category: 'research' | 'strategy' | 'creation' | 'review'
  phase: string
  requires_llm: boolean
  requires_search: boolean
  requires_external_api: boolean
  icon: string
  has_implementation: boolean
  status: string
  output_json_field: string | null
  visible_in_frontend: boolean
}

export type AgentAssignment = {
  id: string
  project_id: string | null
  agent_id: string
  provider_code: string
  model: string
  enabled: boolean
  priority: number
  agent: AgentInfo
  provider_name: string
  provider_label: string
}

export type AIProviderConfig = {
  id: string
  project_id: string | null
  provider: string
  label: string
  api_key_configured: boolean
  base_url: string | null
  last_test_status: string | null
  last_test_error: string | null
  last_tested_at: string | null
  created_at: string
}

// ── Kanban ──────────────────────────────────────────────────────────────

export type KanbanColumn = {
  id: string
  project_id: string
  label: string
  status: string
  color: string | null
  sort_order: number
}

// ── Comments ────────────────────────────────────────────────────────────

export type ArticleComment = {
  id: string
  article_id: string
  author_id: string | null
  author_name: string | null
  parent_id: string | null
  text: string
  selected_text: string | null
  resolved: boolean
  created_at: string
}

// ── Media ───────────────────────────────────────────────────────────────

export type MediaAsset = {
  id: string
  project_id: string
  article_id: string | null
  url: string
  public_url: string | null
  filename: string
  mime_type: string | null
  size: number | null
  alt_text: string | null
  caption: string | null
  source: string | null
  created_at: string
}

// ── Webhooks ────────────────────────────────────────────────────────────

export type Webhook = {
  id: string
  project_id: string
  name: string
  url: string
  events: string[]
  enabled: boolean
  last_triggered_at: string | null
  last_status: string | null
  created_at: string
}

// ── Pipeline ────────────────────────────────────────────────────────────

export type CategoryFrequencyInfo = {
  id: string
  name: string
  monthly_frequency: number | null
  pipeline_enabled: boolean | null
  priority: number
}

export type PipelineSettings = {
  project_id: string
  enabled: boolean
  active_days: string[]
  launch_hour: number
  articles_per_week: number
  category_priorities: Record<string, number>
  ideas_per_week: number | null
  max_pending_drafts: number | null
  max_parallel_writing_jobs: number | null
  paused_until: string | null
  paused_indefinitely: boolean | null
  default_quality_mode: string | null
  ideas_day_of_month: number | null
  publish_hour_start: number | null
  publish_hour_end: number | null
  launch_hours: string[] | null
  cost_limit_per_article_eur: number | null
  total_monthly_from_categories: number | null
  categories_frequencies: CategoryFrequencyInfo[]
  automation_notes: string
  updated_at: string
}

export type PipelineLog = {
  id: string
  project_id: string
  status: string
  workflow_run_id: string | null
  expected_ideas: number
  generated_ideas: number
  failed_categories: Array<Record<string, unknown>>
  run_errors: string[]
  ideas_generated: number
  articles_created: number
  errors: string | null
  started_at: string
  finished_at: string | null
}
