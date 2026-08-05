# External SEO Tools Audit

Audit date: 2026-05-18

Scope:

- `https://github.com/AgriciDaniel/claude-seo`
- `https://github.com/ivankuznetsov/claude-seo`
- `https://github.com/aaron-he-zhu/seo-geo-claude-skills`
- `https://github.com/blader/humanizer`
- Google Search Central and related official Google SEO sources
- Semrush Blog
- Ahrefs Blog
- Neil Patel
- Nelly Kempf

This audit is static only. No external code was executed, no dependencies were installed from these repositories, and nothing is wired into the Ideas Studio runtime.

## A. Repos clonés

| Repo | Local folder | Audited commit | Date du commit | Licence | Type réel |
|---|---|---:|---|---|---|
| `AgriciDaniel/claude-seo` | `external-audit/seo-tools/claude-seo-agrici` | `7676024a0200c8aa636d03dc1de136c1cc8d5ffc` | `2026-05-11` | MIT | Plugin/skills SEO très scripté pour Claude Code |
| `ivankuznetsov/claude-seo` | `external-audit/seo-tools/claude-seo-ivan` | `81284b89275abe14d9ddc048937b5b7e956103d4` | `2026-03-11` | MIT | Workflow prompts + commandes + outils Ruby |
| `aaron-he-zhu/seo-geo-claude-skills` | `external-audit/seo-tools/seo-geo-claude-skills` | `b69ebc6ab437b5b53f0aac375b00a6b713620a30` | `2026-05-14` | Apache-2.0 | Bibliothèque de skills/commands SEO-GEO et benchmarks |
| `blader/humanizer` | `external-audit/seo-tools/humanizer` | `8b3a17889fbf12bedae20974a3c9f9de746ed754` | `2026-03-31` | MIT | Knowledge pack/skill markdown de réécriture |

## B. Audit sécurité

### 1. `claude-seo-agrici`

Résumé sécurité :

- `safe_to_read`: oui
- `safe_to_execute`: non
- `safe_to_vendor`: partiellement, uniquement en snapshot contrôlé de prompts/docs après tri

Scripts et points sensibles détectés :

- installateurs shell/PowerShell :
  - [install.sh](/home/mluca/perso/ideas-studio/external-audit/seo-tools/claude-seo-agrici/install.sh:1)
  - `install.ps1`
  - `uninstall.sh`
  - `uninstall.ps1`
- extensions avec scripts d’installation :
  - `extensions/firecrawl/install.sh`
  - `extensions/dataforseo/install.sh`
  - `extensions/banana/install.sh`
- écritures dans répertoires utilisateur :
  - `~/.claude/skills`
  - `~/.claude/agents`
  - `~/.claude/settings.json`
  - `~/.config/claude-seo/`
- suppression destructive dans les scripts d’uninstall :
  - `rm -rf` dans `uninstall.sh`, `extensions/*/uninstall.sh`
- accès réseau/installation de dépendances :
  - `git clone` dans `install.sh`
  - `pip install` et `python -m playwright install`
  - `npx --yes --package=firecrawl-mcp@...`
  - `urllib.request.urlopen` dans les scripts Banana

Dépendances notables :

- Python : `beautifulsoup4`, `requests`, `lxml`, `playwright`, `Pillow`, `urllib3`, `validators`, `matplotlib`, `weasyprint`, `openpyxl`, Google API libs
- Risque : surface large, accès réseau assumé, setup utilisateur, modules orientés crawl/reporting/API externes

Licence :

- MIT
- usage commercial : oui
- attribution : oui, conserver licence
- risque licence pour Ideas Studio : faible si on reprend seulement des extraits compatibles avec attribution

Secrets :

- pas de vraie clé trouvée dans le clone audité
- nombreuses références à `OPENAI_API_KEY`, `GITHUB_TOKEN`, configs Google/DataForSEO
- risque : le repo attend des secrets utilisateur dans `~/.config/claude-seo/` ou variables d’environnement

Fichiers exécutables / runners :

- nombreux `.sh`, `.ps1`, `.py`
- GitHub Actions CI
- scripts d’API et de fetch

Recommandation :

- ne rien exécuter dans Ideas Studio
- ne pas vendor le code runtime tel quel
- extraire seulement :
  - checklists SEO
  - prompts de brief
  - structure de workflows
  - quelques benchmarks/règles documentaires

### 2. `claude-seo-ivan`

Résumé sécurité :

- `safe_to_read`: oui
- `safe_to_execute`: non
- `safe_to_vendor`: partiellement, surtout prompts/docs, pas les hooks/installers

Scripts et points sensibles détectés :

- hook d’auto-install :
  - [hooks.json](/home/mluca/perso/ideas-studio/external-audit/seo-tools/claude-seo-ivan/hooks/hooks.json:1)
  - [ensure-deps.sh](/home/mluca/perso/ideas-studio/external-audit/seo-tools/claude-seo-ivan/scripts/ensure-deps.sh:1)
- `bundle install` automatique au `SessionStart`
- nombreux accès à variables d’environnement pour GA4/GSC/DataForSEO/Ahrefs dans `data_sources/ruby`

Dépendances notables :

- Ruby/Bundler
- Google API gems
- `faraday`, `faraday-retry`, `nokogiri`, `dotenv`, `oj`, `diskcached`

Licence :

- MIT
- usage commercial : oui
- attribution : oui
- risque licence : faible

Secrets :

- pas de clé réelle détectée
- de nombreuses références à credentials GA4/GSC/DataForSEO/Ahrefs
- le setup pousse vers des fichiers credentials locaux

Fichiers exécutables / runners :

- `scripts/ensure-deps.sh`
- outils Ruby CLI dans `data_sources/ruby/bin/`

Recommandation :

- ne pas exécuter les hooks ni l’auto-install
- ne pas reprendre le runtime Ruby tel quel
- réutilisable comme inspiration forte pour :
  - workflow `research -> write -> humanize -> fact-check -> optimize`
  - checklist de qualité
  - étapes de fact-check et humanization

### 3. `seo-geo-claude-skills`

Résumé sécurité :

- `safe_to_read`: oui
- `safe_to_execute`: non par défaut
- `safe_to_vendor`: oui pour snapshot documentaire/skills sélectionnés, après tri

Scripts et points sensibles détectés :

- scripts de maintenance et validation :
  - `.github/scripts/sync-skills.js`
  - `hooks/claude-hook.sh`
  - `scripts/validate-*.sh`
  - `scripts/recover-retired-warm.sh`
- GitHub Actions
- logique mémoire `memory/` et hooks Claude, non adaptée telle quelle à Ideas Studio

Dépendances :

- pas de runtime package manager principal trouvé pour le cœur des skills
- repo largement markdown-first
- scripts Node/Bash auxiliaires seulement

Licence :

- Apache-2.0
- usage commercial : oui
- attribution : oui
- obligations supplémentaires : conserver notice et mentions de changements si vendor substantiel
- risque licence : faible à modéré, mais bien gérer les notices

Secrets :

- aucune vraie clé détectée
- nombreuses références de config et fichiers de plateforme/marketplace

Fichiers exécutables / runners :

- Bash hooks
- script Node de synchronisation
- scripts shell de validation

Recommandation :

- excellent candidat pour `knowledge packs`
- très bonne base pour :
  - benchmarks EEAT
  - structures de brief
  - audit content/domain
  - workflows GEO/SEO
- ne pas reprendre les hooks/memory système/commandes telles quelles

### 4. `humanizer`

Résumé sécurité :

- `safe_to_read`: oui
- `safe_to_execute`: oui, en tant que simple skill texte revu manuellement
- `safe_to_vendor`: oui, comme knowledge pack ou règles internes réécrites

Scripts et points sensibles détectés :

- pas de code exécutable applicatif
- seulement README et `SKILL.md`
- références à installation dans `~/.claude/skills` et `~/.config/opencode/skills`

Dépendances :

- aucune dépendance package manager détectée

Licence :

- MIT
- usage commercial : oui
- attribution : oui
- risque licence : très faible

Secrets :

- aucun secret détecté

Recommandation :

- très bon candidat pour reprise contrôlée des patterns de “humanization”
- plutôt `knowledge pack` ou réécriture interne des règles

## C. Audit fonctionnel

### 1. `claude-seo-agrici`

Objectif :

- plugin SEO complet pour Claude Code, très large en surface

Type réel :

- plugin/skills/agents + scripts Python + installateurs + extensions externes

Structure utile :

- `skills/seo-flow`
- `skills/seo-content-brief`
- `skills/seo-content`
- `skills/seo-geo`
- `skills/seo-google`
- `scripts/`

Entrées principales :

- `/seo audit`
- `/seo content`
- `/seo flow`
- `/seo geo`
- `/seo google`

Ce qui est réutilisable :

- prompts de brief et d’audit
- FLOW framework
- critères E-E-A-T / GEO
- organisation par capacités

Inspiration seulement :

- orchestration des commandes
- découpage par skill

Ce qui ne sert pas directement à Ideas Studio :

- installateurs
- gestion de plugins Claude
- extensions Banana/Firecrawl/DataForSEO telles quelles

Dangereux tel quel :

- tout le code d’installation et d’auto-configuration utilisateur
- scripts qui modifient `~/.claude` ou lancent `pip`/`npx`

### 2. `claude-seo-ivan`

Objectif :

- workflow éditorial SEO long-form orienté contenu

Type réel :

- prompts + commandes Claude + analyse Ruby optionnelle

Structure utile :

- `commands/seo:research.md`
- `commands/seo:write.md`
- `commands/seo:humanize.md`
- `skills/seo/SKILL.md`
- `data_sources/ruby/bin/`

Ce qui est directement réutilisable :

- logique séquentielle de production
- checklist de rédaction
- checklist de fact-check
- patterns d’humanization

Inspiration seulement :

- outils Ruby CLI
- conventions de fichiers `drafts/`, `published/`, `rewrites/`

Dangereux tel quel :

- auto-install Bundler à l’ouverture de session
- branchements credentials externes sans sandbox

### 3. `seo-geo-claude-skills`

Objectif :

- bibliothèque SEO/GEO structurée avec skills, audits, mémoire, benchmarks

Type réel :

- library de skills markdown + audits + références + commandes

Structure utile :

- `research/keyword-research`
- `research/serp-analysis`
- `research/content-gap-analysis`
- `build/seo-content-writer`
- `cross-cutting/content-quality-auditor`
- `cross-cutting/domain-authority-auditor`
- `monitor/*`

Ce qui est directement réutilisable :

- benchmarks CORE-EEAT et CITE
- structure de brief
- séparation research/build/optimize/monitor
- format d’audit

Inspiration seulement :

- système mémoire HOT/WARM/COLD
- hooks Claude

Dangereux tel quel :

- scripts hooks et système mémoire auto-géré
- coupling fort à un runtime agent/skill externe

### 4. `humanizer`

Objectif :

- retirer les patterns d’écriture “IA visible”

Type réel :

- skill markdown/prompt pack pur

Ce qui est directement réutilisable :

- liste de patterns
- anti-patterns de style
- passe de réécriture finale

Ce qui ne sert pas directement :

- instructions d’installation Claude/OpenCode

Dangereux tel quel :

- rien de critique

## D. Utilité pour Ideas Studio

| Source | Fonction utile | Module Ideas Studio cible | Mode recommandé | Priorité |
|---|---|---|---|---|
| `claude-seo-agrici` | briefs SEO, FLOW, audits de contenu | futur `seo_expert_agent`, brief builder, review service | `A` knowledge pack + `D` inspiration | haute |
| `claude-seo-ivan` | workflow research/write/humanize/fact-check | orchestrateur rédaction, humanization pass, review pass | `A` knowledge pack + `D` inspiration | haute |
| `seo-geo-claude-skills` | benchmarks EEAT/CITE, structure phases, audits | `seo_review_service`, `eeat_checklist_service`, `seo_workflow_orchestrator` | `A` knowledge pack, parfois `C` snapshot docs | très haute |
| `humanizer` | humanization pass | `content_humanization_service` | `A` knowledge pack | moyenne/haute |
| Google Search Central | règles officielles, starter guide, updates | `google_watch_service`, règles SEO internes | `A` knowledge pack + `B` adapter lecture | critique |
| Google Search Status Dashboard | incidents et ranking update feed | `google_watch_service` | `B` adapter | critique |
| Semrush Blog | idées pratiques, AI search, keyword strategy | docs internes/research heuristics | `D` inspiration | moyenne |
| Ahrefs Blog | études, guides, frameworks, exemples | docs internes/research heuristics | `D` inspiration | moyenne |
| Neil Patel | angles éditoriaux grand public | inspiration prudente uniquement | `D` inspiration | basse |
| Nelly Kempf | approche brand SEO + conversion | brief angle, stratégie éditoriale | `D` inspiration | moyenne |

Modes :

- `A` Knowledge pack
- `B` Adapter
- `C` Vendor snapshot
- `D` Inspiration only
- `E` Ne pas intégrer

## E. Plan d’intégration

### Quick wins

- convertir les meilleures checklists en docs internes Ideas Studio
- créer un registre statique de sources/benchmarks
- alimenter le futur SEO Expert Agent avec :
  - règles Google officielles
  - benchmark EEAT/CITE
  - patterns humanizer
  - workflow research/write/review

### Phase 1

- `seo_knowledge_pack_service`
- `seo_tool_registry`
- `google_watch_service`
- `content_humanization_service`
- `seo_review_service`

### Phase 2

- `seo_workflow_orchestrator`
- `seo_expert_agent`
- `seo_source_monitor_service`
- stockage des rapports et veille

### Phase 3

- adapters API optionnels vers vraies sources externes autorisées
- monitoring d’updates et recommandations de refresh article

## F. Sources externes hors GitHub

### Sources officielles Google à privilégier

- Google Search Status Dashboard : `https://status.search.google.com/`
- FAQ du dashboard : `https://developers.google.com/search/help/status-dashboard`
- Google Search Central / SEO Starter Guide : `https://developers.google.com/search/docs/fundamentals/seo-starter-guide`
- Google “Helping creators” / how search works : `https://www.google.com/intl/en_us/search/howsearchworks/our-approach/helping-creators/`

Usage recommandé :

- source normative et prioritaire
- sert aux règles SEO “officielles”
- sert à la veille quotidienne

### Sources secondaires

- Semrush Blog : utile pour tendances, tactiques, AI search, mais source commerciale
- Ahrefs Blog : utile pour guides pratiques, études et exemples, mais source commerciale
- Neil Patel : inspiration marketing grand public, fiabilité plus variable
- Nelly Kempf : utile pour angle brand SEO / pédagogie / acquisition

## G. Recommandations sécurité

À utiliser :

- documents, prompts, benchmarks, checklists, taxonomies, structures de brief

À ne pas exécuter :

- install scripts shell/PowerShell
- hooks `SessionStart`
- `bundle install`, `pip install`, `npx` externes des repos audités
- scripts qui écrivent dans `~/.claude`, `~/.config`, `settings.json`

À sandboxer si un jour adapté :

- appels API externes
- crawling
- veille automatisée
- enrichissement DataForSEO/GSC/GA4

À copier seulement sous forme documentaire :

- benchmarks EEAT/CITE
- patterns de humanization
- templates de brief
- checklists de review

## H. Verdict par repo

| Repo | safe_to_read | safe_to_execute | safe_to_vendor | Verdict |
|---|---|---|---|---|
| `claude-seo-agrici` | oui | non | partiel | inspiration + docs, pas runtime |
| `claude-seo-ivan` | oui | non | partiel | inspiration workflow, pas hooks ni Ruby auto-install |
| `seo-geo-claude-skills` | oui | non | oui partiel | excellent knowledge pack, pas hooks mémoire |
| `humanizer` | oui | oui | oui | très bon knowledge pack |

## I. Prochaines étapes

Urgent :

- valider la stratégie `knowledge pack first`
- ne brancher aucun runtime externe avant approbation
- construire la veille Google officielle

Important :

- extraire les benchmarks utiles dans des packs internes revus
- créer les tables d’audit et d’apprentissage SEO
- préparer un `SEO Expert Agent` modulaire et contrôlé

Plus tard :

- adapters API optionnels
- scoring enrichi avec data externes
- refresh automatique suggéré des articles
