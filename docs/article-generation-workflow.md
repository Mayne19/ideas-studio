# Professional SEO Article Generation Workflow

This document defines the target workflow for Ideas Studio article generation and maps it to the current implementation.

## Goals

- Generate production-usable article drafts.
- Never publish automatically.
- Use a real AI provider in production or fail clearly.
- Preserve user intent, preferred title, and chosen category.
- Produce HTML content compatible with the editor.
- Save structured metadata and generation reports for editorial review.

## Current Safe Foundations

The current codebase already provides these foundations:

- Real LLM provider support via `openai` and `ollama`.
- No silent mock LLM fallback in `production` or `staging`.
- Preferred title is respected in manual generation flows.
- `category_id` can be passed through generation and saved on the article.
- Generated content is converted from Markdown to HTML before saving.
- Generated drafts remain unpublished.
- `reading_time_minutes` is calculated automatically.
- `faq_json` can be generated separately from the main article body.

## Target Workflow

### Phase 0: Project Context

Create a `ProjectContext` object before generation:

- project identity: name, domain, language, audience
- editorial setup: tone, positioning, constraints
- available categories
- available callout templates
- published article inventory
- already used keywords if available
- FAQ support

Recommended shape:

```json
{
  "project_id": "...",
  "site_name": "...",
  "domain": "...",
  "language": "fr",
  "audience": "...",
  "tone": "...",
  "categories": [],
  "callout_templates": [],
  "published_articles": [],
  "faq_enabled": true
}
```

### Phase 1: Topic Brief

Generate or validate a `TopicBrief`.

Manual mode:

- respect `preferred_title`
- preserve `category_id` if provided
- preserve `keyword`, `audience`, `angle`, `search_intent` if provided

Pipeline mode:

- choose a category deliberately
- justify the topic choice
- do not pick randomly

Recommended shape:

```json
{
  "title": "...",
  "category_id": "...",
  "reason": "...",
  "objective": "...",
  "reader_profile": "..."
}
```

### Phase 2: Intent Analysis

Add a dedicated `IntentAnalysis` step before outline or drafting.

Required outputs:

- explicit question
- implicit need
- practical expectations
- information to avoid
- recommended angle
- expected depth

Rule:

- the first `H2` must answer the main question directly

### Phase 3: Research Brief

Build a `ResearchBrief` from allowed sources:

- SERP summaries
- public question clusters
- expert pages
- public community signals when legally accessible

Required outputs:

- sources used
- recurring questions
- concrete frictions
- facts and data points
- competitor gaps
- opportunities to do better

Important:

- if a source is not available, report that explicitly
- never invent citations or data

### Phase 4: Keyword Brief

Generate a `KeywordBrief`:

- `main_keyword`
- `secondary_keywords`
- `related_questions`
- `entities`
- `usage_strategy`

This phase should support intelligent long-tail matching, not exact-string stuffing only.

### Phase 5: Editorial Angle

Generate an `EditorialAngle`:

- promise
- main angle
- tone
- EEAT opportunities
- callout opportunities
- FAQ recommendation

### Phase 6: Structured Outline

Persist a richer outline than the current `outline_json`:

- `H1`
- introduction intent
- first `H2` direct answer
- ordered sections with roles
- optional `H3/H4`
- planned FAQ
- planned callouts

Rule:

- no isolated single `H3` under one `H2`

### Phase 7: Drafting

Draft a full article body:

- minimum words configurable
- HTML-compatible output
- no markdown leaks
- developed paragraphs
- examples and practical guidance
- optional tables, lists, blockquotes

### Phase 8: Callout Plan

Create a `CalloutPlan` using project templates:

- template used
- placement
- title
- text
- reason

If no useful callout exists, omit callouts instead of forcing them.

### Phase 9: FAQ

Generate `faq_json` only when justified:

- minimum 2 questions
- maximum 6 questions
- derived from real reader blocks or search signals

### Phase 10: EEAT Checklist

Add an `EEATChecklist`:

- expertise strengthened
- sources included
- examples included
- limits and nuance included
- trust signals included

This checklist must never invent personal experience or fake authority.

### Phase 11: Originality Report

Add an `OriginalityReport`:

- real tool if integrated, otherwise heuristic only
- passages at risk
- rewriting needs

Be explicit when the originality check is heuristic.

### Phase 12: Quality Pass

Add a `QualityPassReport`:

- grammar
- repetition
- sentence length
- paragraph length
- clarity
- tone

### Phase 13: Final SEO Checklist

Persist a `SEOChecklist` at generation time:

- title
- meta title
- meta description
- slug
- intro keyword use
- heading quality
- smart slug keyword match
- internal and external links
- image alt coverage
- article length
- FAQ usefulness

### Phase 14: Save Draft

Save the article as a draft only:

- `status = draft_ready`
- `published = false`
- `content = HTML`
- `title`
- `slug`
- `category_id`
- `meta_title`
- `meta_description`
- `excerpt`
- `keyword`
- `reading_time_minutes`
- `faq_json`
- `callouts_json`
- `generation_report_json`
- `sources_json`
- `seo_checklist_json`

### Phase 15: Visible Generation Report

Expose a readable report in the editor or generation result screen:

- provider and model used
- title respected or adjusted
- chosen category
- source summary
- detected intent
- outline
- FAQ generated
- callouts proposed
- quality or SEO warnings

## Recommended Backend Architecture

### Services

- `project_context_service.py`
  - builds `ProjectContext`
- `topic_brief_service.py`
  - validates user topic or selects pipeline topic
- `intent_analysis_service.py`
  - creates `IntentAnalysis`
- `research_service.py`
  - assembles `ResearchBrief`
- `keyword_strategy_service.py`
  - creates `KeywordBrief`
- `editorial_angle_service.py`
  - creates `EditorialAngle`
- `outline_service.py`
  - creates structured outline JSON
- `drafting_service.py`
  - generates content HTML and optional FAQ/callout drafts
- `quality_service.py`
  - quality, originality, EEAT, SEO reports
- `generation_workflow_service.py`
  - orchestrates all phases and persists outputs

### Persisted JSON Fields

Recommended additions on `Article`:

- `generation_report_json`
- `sources_json`
- `seo_checklist_json`
- `intent_analysis_json`
- `keyword_brief_json`
- `research_brief_json`
- `editorial_angle_json`
- `quality_report_json`

If adding all fields is too heavy, start with:

- `generation_report_json`
- `sources_json`
- `seo_checklist_json`

### Endpoints

Keep current endpoints but make the orchestration explicit:

- `POST /projects/{project_id}/ideas/generate`
- `POST /articles/{article_id}/start-writing`
- `POST /projects/{project_id}/launch`

Recommended additions later:

- `GET /articles/{article_id}/generation-report`
- `POST /projects/{project_id}/pipeline/run`
  - remain ideas-only until full auto-draft generation is truly implemented

## Current Gap Summary

### Already Present

- provider safety in production
- preferred title support
- category persistence
- HTML content output
- reading time calculation
- FAQ extraction
- draft-only generation

### Partial

- project context
- topic selection
- keyword strategy
- outline quality
- pipeline scheduling

### Missing

- intent analysis
- research brief
- editorial angle object
- callout planning
- EEAT report
- originality report
- quality report
- visible generation report
- persisted SEO checklist JSON

## Safe Implementation Priorities

### Urgent

- keep real provider enforcement
- keep draft-only guarantee
- keep user title and category propagation
- add visible generation report storage

### Important

- add `IntentAnalysis`
- add `ResearchBrief`
- add `KeywordBrief`
- strengthen outline structure and source capture

### Later

- intelligent callout placement
- EEAT checklist
- originality checks
- full automated pipeline with category priorities

