import { ReportSection, ReportGroup } from './ReportSection'
import type { EditorArticle } from '@/types'

export default function BriefPanel({ article }: { article: EditorArticle }) {
  const hasContent = article.research_brief_json || article.keyword_brief_json || article.editorial_angle_json || article.intent_analysis_json

  if (!hasContent) return null

  return (
    <ReportGroup title="Briefs">
      {article.research_brief_json && <ReportSection title="Brief Recherche" data={article.research_brief_json} />}
      {article.keyword_brief_json && <ReportSection title="Brief Mots-clés" data={article.keyword_brief_json} />}
      {article.editorial_angle_json && <ReportSection title="Angle éditorial" data={article.editorial_angle_json} />}
      {article.intent_analysis_json && <ReportSection title="Analyse d'intention" data={article.intent_analysis_json} />}
    </ReportGroup>
  )
}
