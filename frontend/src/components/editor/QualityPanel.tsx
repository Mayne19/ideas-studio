import { ReportSection, ReportGroup } from './ReportSection'
import type { EditorArticle } from '@/types'

export default function QualityPanel({ article }: { article: EditorArticle }) {
  const languageQuality = article.artifacts['language_quality_report']
  const originality = article.artifacts['originality_report']
  const humanization = article.artifacts['humanization_report']
  const editorialQuality = article.artifacts['editorial_quality_report']
  const eeatChecklist = article.artifacts['eeat_checklist']
  const seoFinalChecklist = article.artifacts['seo_final_checklist']
  const cannibalizationCheck = article.artifacts['cannibalization_check']
  const hasContent = languageQuality || originality || humanization || editorialQuality || eeatChecklist || seoFinalChecklist || cannibalizationCheck

  if (!hasContent) return null

  return (
    <ReportGroup title="Qualité">
      {languageQuality && <ReportSection title="Qualité linguistique" data={languageQuality} />}
      {originality && <ReportSection title="Originalité" data={originality} />}
      {humanization && <ReportSection title="Humanisation" data={humanization} />}
      {editorialQuality && <ReportSection title="Qualité éditoriale" data={editorialQuality} />}
      {eeatChecklist && <ReportSection title="EEAT" data={eeatChecklist} />}
      {seoFinalChecklist && <ReportSection title="Checklist SEO finale" data={seoFinalChecklist} />}
      {cannibalizationCheck && <ReportSection title="Check cannibalisation" data={cannibalizationCheck} />}
    </ReportGroup>
  )
}
