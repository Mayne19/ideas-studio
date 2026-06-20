import { ReportSection, ReportGroup } from './ReportSection'
import type { EditorArticle } from '@/types'

export default function QualityPanel({ article }: { article: EditorArticle }) {
  const hasContent = article.language_quality_report_json || article.originality_report_json || article.humanization_report_json || article.editorial_quality_report_json || article.eeat_checklist_json || article.seo_final_checklist_json || article.cannibalization_check_json

  if (!hasContent) return null

  return (
    <ReportGroup title="Qualité">
      {article.language_quality_report_json && <ReportSection title="Qualité linguistique" data={article.language_quality_report_json} />}
      {article.originality_report_json && <ReportSection title="Originalité" data={article.originality_report_json} />}
      {article.humanization_report_json && <ReportSection title="Humanisation" data={article.humanization_report_json} />}
      {article.editorial_quality_report_json && <ReportSection title="Qualité éditoriale" data={article.editorial_quality_report_json} />}
      {article.eeat_checklist_json && <ReportSection title="EEAT" data={article.eeat_checklist_json} />}
      {article.seo_final_checklist_json && <ReportSection title="Checklist SEO finale" data={article.seo_final_checklist_json} />}
      {article.cannibalization_check_json && <ReportSection title="Check cannibalisation" data={article.cannibalization_check_json} />}
    </ReportGroup>
  )
}
