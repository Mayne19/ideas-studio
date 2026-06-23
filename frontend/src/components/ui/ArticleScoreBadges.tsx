import type { Article } from '@/types'
import { finiteScore, getOriginalityScore, getGeoScore } from '@/lib/scoreBadge'
import ScoreBadge from '@/components/ui/ScoreBadge'

interface ArticleScoreBadgesProps {
  article: Article
  compact?: boolean
  className?: string
}

export default function ArticleScoreBadges({ article, compact = false, className = '' }: ArticleScoreBadgesProps) {
  return (
    <div className={`flex flex-wrap items-center gap-x-2.5 gap-y-1.5 ${className}`}>
      <ScoreBadge label="Global" value={finiteScore(article.global_score)} compact={compact} />
      <ScoreBadge label="SEO" value={finiteScore(article.seo_score)} compact={compact} />
      <ScoreBadge label="Qualité" value={finiteScore(article.quality_score)} compact={compact} />
      <ScoreBadge label="Lisibilité" value={finiteScore(article.readability_score)} compact={compact} />
      <ScoreBadge label="Originalité" value={getOriginalityScore(article)} compact={compact} />
      <ScoreBadge label="GEO" value={getGeoScore(article)} compact={compact} />
      <ScoreBadge label="EEAT" value={finiteScore(article.eeat_score)} compact={compact} />
    </div>
  )
}
