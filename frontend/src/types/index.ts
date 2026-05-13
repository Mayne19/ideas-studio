export type User = {
  id: string
  name: string
  email: string
  created_at: string
}

export type Project = {
  id: string
  owner_id: string
  name: string
  domain: string | null
  language: string | null
  country_target: string | null
  audience: string | null
  tone: string | null
  status: string
  public_tracking_key: string
  connected_at: string | null
  last_seen_at: string | null
  created_at: string
  updated_at: string
}

export type ProjectRole = 'owner' | 'admin' | 'editor' | 'writer' | 'designer' | 'viewer'

export type ProjectMember = {
  id: string
  user_id: string
  user_name: string | null
  user_email: string | null
  role: ProjectRole
  status: string
  created_at: string
}

export type ConnectInfo = {
  project_id: string
  domain: string | null
  status: string
  public_tracking_key: string
  secret_api_key: string | null
  secret_api_key_masked: string
  connected_at: string | null
  last_seen_at: string | null
  snippet: string
  public_api_endpoints: Record<string, string>
}

export type LoginResponse = {
  access_token: string
  token_type: string
}

export type ArticleStatus =
  | 'draft'
  | 'idea_proposed'
  | 'idea_priority'
  | 'idea_rejected'
  | 'outline_ready'
  | 'writing_requested'
  | 'writing_in_progress'
  | 'draft_ready'
  | 'review_needed'
  | 'correction_needed'
  | 'scheduled'
  | 'published'
  | 'ready_to_publish'
  | 'update_recommended'
  | 'unpublished'
  | 'archived'
  | 'failed'

export type Article = {
  id: string
  project_id: string
  category_id: string | null
  title: string
  slug: string
  status: ArticleStatus
  keyword: string | null
  content: string | null
  excerpt: string | null
  meta_title: string | null
  meta_description: string | null
  cover_image_url: string | null
  word_count: number
  priority: number
  seo_score: number | null
  readability_score: number | null
  quality_score: number | null
  eeat_score: number | null
  readiness_status: string | null
  scheduled_at: string | null
  published_at: string | null
  // Idea-specific fields
  angle: string | null
  search_intent: string | null
  opportunity_score: number | null
  audience: string | null
  rejection_reason: string | null
  rejection_note: string | null
  created_at: string
  updated_at: string
}

export type IdeaStatus = 'idea_proposed' | 'idea_priority' | 'idea_rejected'

export type IdeaGenerateRequest = {
  context_hint?: string | null
}

export type IdeaGenerateResponse = {
  id: string
  title: string
  keyword: string | null
  angle: string | null
  search_intent: string | null
  audience: string | null
  opportunity_score: number | null
  status: string
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
}

export type IdeaLaunchResponse = {
  project_id: string
  mode: string
  dry_run: boolean
  ideas_generated: number
  article_ids: string[]
}

export const IDEA_STATUSES: IdeaStatus[] = ['idea_proposed', 'idea_priority', 'idea_rejected']

export const WRITING_STATUSES: ArticleStatus[] = ['outline_ready', 'writing_requested', 'writing_in_progress']

export type Category = {
  id: string
  project_id: string
  name: string
  slug: string
  description: string | null
  color: string | null
  priority: number
  target_frequency: number | null
  created_at: string
  updated_at: string
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
  readiness_status: string | null
  created_at: string
}

export type SeoAnalysis = {
  id: string
  article_id: string
  project_id: string
  seo_score: number | null
  readability_score: number | null
  quality_score: number | null
  eeat_score: number | null
  readiness_status: string | null
  issues: SeoIssue[]
  suggestions: string[]
  created_at: string
}

export type ReadyCheck = {
  article_id: string
  readiness_status: string | null
  seo_score: number | null
  readability_score: number | null
  quality_score: number | null
  eeat_score: number | null
  blocking_issues: SeoIssue[]
  can_publish: boolean
}

export type ArticleVersion = {
  id: string
  article_id: string
  project_id: string
  title: string
  slug: string
  version_number: number
  version_type: 'manual' | 'autosave' | 'restore'
  created_by: string | null
  created_at: string
}

export type EditorArticle = Article & {
  faq_json: unknown | null
  callouts_json: unknown | null
  internal_links_json: unknown | null
  external_links_json: unknown | null
  content_blocks_json: unknown | null
  latest_analysis: AnalysisBrief | null
}

export type AutosaveRequest = {
  title?: string | null
  slug?: string | null
  content?: string | null
  excerpt?: string | null
  meta_title?: string | null
  meta_description?: string | null
  cover_image_url?: string | null
  faq_json?: unknown | null
  callouts_json?: unknown | null
  internal_links_json?: unknown | null
  external_links_json?: unknown | null
  content_blocks_json?: unknown | null
  category_id?: string | null
}

export type AutosaveResponse = {
  id: string
  word_count: number
  updated: boolean
  version_created: boolean
  updated_at: string
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
  total_views: number
  unique_pages: number
  top_pages: TopPage[]
  referrers: TrafficReferrer[]
  countries: TrafficCountry[]
  devices: TrafficDevice[]
  trend_by_day: TrafficTrendPoint[]
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
  updated_at: string
}
