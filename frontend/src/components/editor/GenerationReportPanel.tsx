import { ReportSection, ReportGroup } from './ReportSection'
import type { EditorArticle } from '@/types'

export default function GenerationReportPanel({ article }: { article: EditorArticle }) {
  const hasContent = article.generation_report_json

  if (!hasContent) return null

  return (
    <ReportGroup title="Génération">
      <ReportSection title="Rapport de génération" data={article.generation_report_json} />
    </ReportGroup>
  )
}
