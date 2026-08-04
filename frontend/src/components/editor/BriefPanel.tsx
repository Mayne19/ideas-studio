import { ReportSection, ReportGroup } from './ReportSection'
import type { EditorArticle } from '@/types'

export default function BriefPanel({ article }: { article: EditorArticle }) {
  const researchBrief = article.artifacts['research_brief']
  const keywordBrief = article.artifacts['keyword_brief']
  const editorialAngle = article.artifacts['editorial_angle']
  const intentAnalysis = article.artifacts['intent_analysis']
  const hasContent = researchBrief || keywordBrief || editorialAngle || intentAnalysis

  if (!hasContent) return null

  return (
    <ReportGroup title="Briefs">
      {researchBrief && <ReportSection title="Brief Recherche" data={researchBrief} />}
      {keywordBrief && <ReportSection title="Brief Mots-clés" data={keywordBrief} />}
      {editorialAngle && <ReportSection title="Angle éditorial" data={editorialAngle} />}
      {intentAnalysis && <ReportSection title="Analyse d'intention" data={intentAnalysis} />}
    </ReportGroup>
  )
}
