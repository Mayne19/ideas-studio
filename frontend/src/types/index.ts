export type User = {
  id: string
  username: string | null
  name: string
  first_name: string | null
  last_name: string | null
  email: string
  avatar_url: string | null
  created_at: string
}

export type Project = {
  id: string
  owner_id: string
  name: string
  domain: string | null
  language: string | null
  vertical: string | null
  country_target: string | null
  timezone: string | null
  description: string | null
  industry: string | null
  audience: string | null
  tone: string | null
  reader_level: string | null
  writing_style: string | null
  editorial_goal: string | null
  value_proposition: string | null
  allowed_topics: string | null
  forbidden_topics: string | null
  words_to_avoid: string | null
  average_target_length: string | null
  preferred_formats: string | null
  technical_level: string | null
  seo_rules: string | null
  geo_rules: string | null
  source_guidelines: string | null
  internal_linking_guidelines: string | null
  external_linking_guidelines: string | null
  style_examples: string | null
  status: string
  public_tracking_key: string
  connected_at: string | null
  last_seen_at: string | null
  public_site_url: string | null
  revalidate_url: string | null
  revalidate_secret_configured: boolean
  last_revalidated_at: string | null
  last_revalidate_status: string | null
  last_revalidate_error: string | null
  created_at: string
  updated_at: string
}

export type ProjectRole = 'owner' | 'admin' | 'editor' | 'writer' | 'viewer'

export type ActivityLog = {
  id: string
  project_id: string
  user_id: string
  user_name: string | null
  action: string
  resource_type: string | null
  resource_id: string | null
  description: string | null
  metadata: Record<string, unknown> | null
  created_at: string
}

export type ProjectMember = {
  id: string
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
  status: string
  public_tracking_key: string
  secret_api_key_masked: string
  connected_at: string | null
  last_seen_at: string | null
  snippet: string
  public_api_endpoints: Record<string, string>
  public_site_url: string | null
  revalidate_url: string | null
  revalidate_secret_configured: boolean
  last_revalidated_at: string | null
  last_revalidate_status: string | null
  last_revalidate_error: string | null
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
  | 'improvement_proposed'
  | 'improvement_in_progress'
  | 'improvement_ready'

export type Article = {
  id: string
  project_id: string
  category_id: string | null
  sub_niche: string | null
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
  featured: boolean
  seo_score: number | null
  readability_score: number | null
  quality_score: number | null
  eeat_score: number | null
  readiness_status: string | null
  global_score: number | null
  global_score_valid: boolean | null
  is_validable: boolean | null
  validation_reasons: string[]
  critical_warnings: Array<{ type: string; severity: string; message: string }>
  author_name: string | null
  reading_time_minutes: number | null
  scheduled_at: string | null
  published_at: string | null
  // Idea-specific fields
  angle: string | null
  search_intent: string | null
  opportunity_score: number | null
  audience: string | null
  rejection_reason: string | null
  rejection_note: string | null
  // Workflow tracking
  workflow_run_id: string | null
  completed_agent_keys: string | null
  next_agent_key: string | null
  agent_outputs_json: Record<string, unknown> | null
  planning_brief_json: Record<string, unknown> | null
  production_brief_json: Record<string, unknown> | null
  workflow_status: string | null
  // Target dates
  target_write_at: string | null
  target_review_at: string | null
  // Pre-brief fields
  main_answer_summary: string | null
  opportunity_justification: string | null
  recommended_format: string | null
  target_word_count: number | null
  needs_faq: boolean | null
  needs_images: boolean | null
  suggested_internal_links: string | null
  suggested_external_links: string | null
  estimated_difficulty: string | null
  proposal_source: string | null
  secondary_keywords_json: string | null
  // Monitoring / improvement
  improvement_proposal_json: Record<string, unknown> | null
  performance_diagnosis_json: Record<string, unknown> | null
  original_article_id: string | null
  revision_of_article_id: string | null
  proposed_changes_json: Record<string, unknown> | null
  improvement_reason: string | null
  monitoring_status: string | null
  next_review_at: string | null
  created_at: string
  updated_at: string
  // Extended fields
  generation_report_json: Record<string, unknown> | null
  human_validated_at: string | null
  estimated_cost_json: Record<string, unknown> | null
  actual_cost_json: Record<string, unknown> | null
  geo_optimization_json: Record<string, unknown> | null
  originality_report_json: Record<string, unknown> | null
  content_format: 'short' | 'medium' | 'long' | 'pillar' | null
}

export type IdeaStatus = 'idea_proposed' | 'idea_priority' | 'idea_rejected'

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
  angle: string | null
  search_intent: string | null
  audience: string | null
  opportunity_score: number | null
  status: string
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
  monthly_frequency: number | null
  pipeline_enabled: boolean | null
  priority_score: number | null
  editorial_goal: string | null
  target_audience: string | null
  internal_notes: string | null
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
  settings_json: string | null
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
  readiness_status: string | null
  seo_score: number | null
  readability_score: number | null
  quality_score: number | null
  eeat_score: number | null
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
  seo_review_json: SeoExpertReview | null
  generation_report_json: Record<string, unknown> | null
  project_context_json: Record<string, unknown> | null
  category_strategy_json: Record<string, unknown> | null
  idea_discovery_json: Record<string, unknown> | null
  intent_analysis_json: Record<string, unknown> | null
  research_brief_json: Record<string, unknown> | null
  keyword_brief_json: Record<string, unknown> | null
  cannibalization_check_json: Record<string, unknown> | null
  editorial_angle_json: Record<string, unknown> | null
  outline_json: unknown | null
  image_plan_json: Record<string, unknown> | null
  image_sources_json: Record<string, unknown> | null
  callout_plan_json: Record<string, unknown> | null
  language_quality_report_json: Record<string, unknown> | null
  originality_report_json: Record<string, unknown> | null
  humanization_report_json: Record<string, unknown> | null
  eeat_checklist_json: Record<string, unknown> | null
  editorial_quality_report_json: Record<string, unknown> | null
  seo_final_checklist_json: Record<string, unknown> | null
  sources_json: Record<string, unknown> | null
  serp_analysis_json: Record<string, unknown> | null
  extracted_sources_json: Record<string, unknown> | null
  content_gap_json: Record<string, unknown> | null
  source_quality_report_json: Record<string, unknown> | null
  evidence_pack_json: Record<string, unknown> | null
  style_guide_json: Record<string, unknown> | null
  cannibalization_outline_json: Record<string, unknown> | null
  claims_json: Record<string, unknown> | null
  fact_check_report_json: Record<string, unknown> | null
  estimated_cost_json: Record<string, unknown> | null
  geo_optimization_json: Record<string, unknown> | null
  structured_data_json: Record<string, unknown> | null
  readability_report_json: Record<string, unknown> | null
  content_format: 'short' | 'medium' | 'long' | 'pillar' | null
  latest_analysis: AnalysisBrief | null
  published_content: string | null
  published_title: string | null
  published_excerpt: string | null
  published_meta_description: string | null
  published_cover_image_url: string | null
  published_faq_json: unknown | null
  published_callouts_json: unknown | null
  has_draft_changes: boolean | null
}

export type AutosaveRequest = {
  title?: string | null
  slug?: string | null
  content?: string | null
  excerpt?: string | null
  keyword?: string | null
  meta_title?: string | null
  meta_description?: string | null
  cover_image_url?: string | null
  faq_json?: unknown | null
  callouts_json?: unknown | null
  internal_links_json?: unknown | null
  external_links_json?: unknown | null
  content_blocks_json?: unknown | null
  category_id?: string | null
  sub_niche?: string | null
  featured?: boolean | null
  author_name?: string | null
  reading_time_minutes?: number | null
  content_format?: 'short' | 'medium' | 'long' | 'pillar' | null
  target_word_count?: number | null
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
  updated_at: string
}

export type Invitation = {
  id: string
  project_id: string
  email: string
  role: string
  token: string
  invited_by_user_id: string
  target_user_id: string | null
  accepted_at: string | null
  expires_at: string
  created_at: string
}

export type InvitationCreateResult = Invitation

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
  provider_id: string
  enabled: boolean
  priority: number
  created_at: string
  updated_at: string
  agent: AgentInfo
  provider_name: string
  provider_label: string
}

export type AIProviderConfig = {
  id: string
  project_id: string | null
  provider: string
  label: string
  display_name: string | null
  api_key_configured: boolean
  model: string | null
  base_url: string | null
  is_default: boolean
  enabled: boolean
  last_test_status: string | null
  last_test_error: string | null
  last_tested_at: string | null
  created_at: string
  updated_at: string
}
