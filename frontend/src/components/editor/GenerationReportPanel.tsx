import { ReportSection, ReportGroup } from './ReportSection'
import type { EditorArticle } from '@/types'

export default function GenerationReportPanel({ article }: { article: EditorArticle }) {
  const report = article.artifacts['generation_report']

  if (!report) return null

  return (
    <ReportGroup title="Génération">
      <ReportSection title="Rapport de génération" data={report} />
    </ReportGroup>
  )
}
