# SEO Expert Agent Tooling Strategy

This document defines how Ideas Studio should integrate external SEO know-how without importing unsafe runtime code.

## Principles

- External repositories are audit inputs, not trusted runtime dependencies.
- No auto-install, no self-modifying code, no unreviewed external execution.
- Prefer official Google guidance over commercial blog advice when rules conflict.
- Use commercial/blog sources as heuristics, examples, and idea generators.
- Keep every integration mode explicit: knowledge pack, adapter, vendor snapshot, inspiration only, or reject.

## 1. Integration Modes

### A. Knowledge Pack

Use when we want:

- prompts
- checklists
- scoring rubrics
- writing constraints
- EEAT or GEO frameworks

Implementation:

- rewrite into Ideas Studio owned docs or static Python constants
- no external code execution

Best candidates:

- `humanizer`
- selected `seo-geo-claude-skills` benchmark content
- selected `claude-seo-agrici` brief and audit prompts
- selected `claude-seo-ivan` workflow checklists
- Google Search Central guidance

### B. Adapter

Use when we want controlled access to a source or API.

Implementation:

- write our own service
- whitelist endpoints
- sanitize inputs and outputs
- log usage

Best candidates:

- Google Search Status Dashboard
- Google documentation update watcher
- future GSC/GA4 adapters

### C. Vendor Snapshot

Use only when a small, high-value, low-risk asset should be frozen in-tree.

Requirements:

- license review complete
- exact commit hash recorded
- no auto-update
- local modifications documented

Best candidates:

- small benchmark markdown files
- static schemas or templates

### D. Inspiration Only

Use when the idea is useful but the implementation is too coupled, too broad, or too risky.

Best candidates:

- most of `claude-seo-agrici` runtime scripts
- most of `claude-seo-ivan` Ruby execution layer
- commercial blog workflows

### E. Do Not Integrate

Use when:

- installer modifies user system
- hook auto-installs dependencies
- code assumes uncontrolled secrets or writes outside app scope
- repo is too runtime-specific for Ideas Studio

## 2. Proposed Architecture

### Core Services

- `seo_expert_agent.py`
  - orchestrates the end-to-end SEO review and drafting preparation
- `seo_tool_registry.py`
  - central registry of approved tools, sources, and integration modes
- `seo_knowledge_pack_service.py`
  - loads owned prompts, checklists, and benchmark snippets
- `google_watch_service.py`
  - polls official Google sources and stores update events
- `seo_workflow_orchestrator.py`
  - coordinates research, brief, review, and reporting steps
- `seo_review_service.py`
  - runs SEO, EEAT, and quality checks on drafts
- `content_humanization_service.py`
  - applies safe humanization heuristics to generated drafts
- `seo_source_monitor_service.py`
  - monitors approved external sources and deduplicates changes

### Responsibilities

`seo_expert_agent.py`

- chooses which internal tools to use
- never executes unapproved external code
- builds one combined report for the editor

`seo_knowledge_pack_service.py`

- serves:
  - Google official rules
  - humanization patterns
  - EEAT benchmark items
  - content brief structures
  - GEO checklist items

`google_watch_service.py`

- watches:
  - Search Status Dashboard
  - Search Central docs changes when detectable
  - Google core update documentation
  - helpful content / people-first guidance

`seo_review_service.py`

- scores draft quality
- merges native analyzer output and knowledge-pack checklists

## 3. Recommended Data Model

Add controlled storage tables later:

- `seo_knowledge_items`
  - internal normalized rules, prompts, benchmark items
- `seo_external_tool_audits`
  - repo/source audit reports with commit hashes and risk verdicts
- `seo_update_events`
  - Google or SEO ecosystem updates with severity and summary
- `seo_article_reviews`
  - per-article SEO, EEAT, readability, trust review results
- `seo_generation_reports`
  - generation briefs, chosen sources, quality notes, warnings
- `seo_learning_notes`
  - approved lessons from human feedback and editorial decisions
- `seo_prompt_versions`
  - versioned prompt packs and rollout metadata

## 4. Future Endpoints

Not to implement yet, but recommended:

- `GET /projects/{project_id}/seo/knowledge-packs`
- `GET /projects/{project_id}/seo/updates`
- `POST /projects/{project_id}/seo/review`
- `POST /projects/{project_id}/seo/humanize`
- `GET /articles/{article_id}/seo-report`
- `POST /projects/{project_id}/seo/watch/run`

## 5. Google Watch Strategy

### Priority Sources

- Google Search Status Dashboard
- Google Search Central documentation
- Google SEO Starter Guide
- Google core update guidance
- Google helpful people-first content guidance

### Cadence

- official Google status and updates: daily
- secondary SEO blogs: weekly
- published article refresh audit: weekly
- full site audit: monthly

### Method

1. Fetch official source metadata or content snapshot.
2. Normalize source URL, title, timestamp, and body excerpt.
3. Hash normalized content to deduplicate.
4. Compare with last seen snapshot.
5. If changed:
   - classify impact: low, medium, important, critical
   - summarize change
   - attach source URL
   - generate recommended actions for Ideas Studio users

### Safety Rules

- never invent Google updates
- always preserve source URL
- never escalate a rumor as an official update

## 6. Source Hierarchy

When sources disagree:

1. Google official documentation and dashboards
2. First-party product documentation or data
3. High-quality studies and transparent methodology
4. Reputable practitioner blogs
5. Generic commercial blog content

This hierarchy should drive the future review agent.

## 7. Suggested Mapping

### Google official sources

- mode: `A + B`
- use for:
  - policies
  - status watching
  - SEO rules baseline

### `seo-geo-claude-skills`

- mode: `A`, sometimes `C`
- use for:
  - EEAT benchmark
  - content and domain review rubrics
  - content brief structure

### `claude-seo-agrici`

- mode: `A + D`
- use for:
  - FLOW workflow concepts
  - brief and audit patterns

### `claude-seo-ivan`

- mode: `A + D`
- use for:
  - editorial pipeline shape
  - humanization and fact-check phase ordering

### `humanizer`

- mode: `A`
- use for:
  - humanization patterns and final pass checklist

### Semrush / Ahrefs / Neil Patel / Nelly Kempf

- mode: `D`
- use for:
  - examples
  - educational heuristics
  - tactical inspiration

## 8. What To Build Next

### Quick wins

- normalize internal knowledge packs
- add a static tool registry
- add a Google update watcher plan

### Phase 1

- internal benchmark packs
- Google watcher data model
- humanization pass service
- SEO review report model

### Phase 2

- full `seo_expert_agent`
- generation + review report in editor
- source monitor summaries

### Phase 3

- optional API adapters with explicit project-level configuration
- post-publication recommendations and refresh workflows
