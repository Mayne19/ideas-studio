import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Pencil } from '@/components/ui/hugeIcons'
import { getEditorArticle } from '@/api/editor'
import type { EditorArticle } from '@/types'
import Button from '@/components/ui/Button'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import StatusBadge from '@/components/ui/StatusBadge'
import { useAuth } from '@/context/AuthContext'
import { formatDate } from '@/utils/format'

type FaqItem = { question: string; answer: string }
type OutlineItem = { id: string; level: number; text: string }

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

function sanitizeHtml(html: string): string {
  return html
    .replace(/<span([^>]*data-comment-id=["'][^"']+["'][^>]*)>/gi, '<span$1>')
    .replace(/\sclass=["'][^"']*comment-mark[^"']*["']/gi, '')
    .replace(/\sdata-comment-id=["'][^"']+["']/gi, '')
    .replace(/<p>\s*#[^<\s][^<]*<\/p>/gi, '')
    .replace(/<p>\s*(extrait|excerpt)\s*:?\s*[^<]*<\/p>/gi, '')
}

function renderContent(content: string): string {
  if (/<[a-z][\s\S]*>/i.test(content)) return sanitizeHtml(content)

  return content
    .split(/\n{2,}/)
    .map((block) => {
      const text = block.trim()
      if (!text || /^#[\w-]+$/i.test(text)) return ''
      if (text.startsWith('#### ')) return `<h4>${escapeHtml(text.slice(5))}</h4>`
      if (text.startsWith('### ')) return `<h3>${escapeHtml(text.slice(4))}</h3>`
      if (text.startsWith('## ')) return `<h2>${escapeHtml(text.slice(3))}</h2>`
      if (text.startsWith('# ')) return `<h1>${escapeHtml(text.slice(2))}</h1>`
      if (text.startsWith('> ')) return `<blockquote>${escapeHtml(text.slice(2))}</blockquote>`
      return `<p>${escapeHtml(text).replace(/\n/g, '<br />')}</p>`
    })
    .join('')
}

function stripHtml(value: string): string {
  return value.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim()
}

function parseFaqItems(value: unknown): FaqItem[] {
  if (Array.isArray(value)) {
    return value.filter((item): item is FaqItem =>
      item !== null &&
      typeof item === 'object' &&
      typeof (item as FaqItem).question === 'string' &&
      typeof (item as FaqItem).answer === 'string'
    )
  }
  if (typeof value === 'string' && value.trim()) {
    try {
      return parseFaqItems(JSON.parse(value))
    } catch {
      return []
    }
  }
  return []
}

function buildOutline(html: string): OutlineItem[] {
  const outline: OutlineItem[] = []

  const headingRegex = /<h([2-4])[^>]*>([\s\S]*?)<\/h\1>/gi
  let match: RegExpExecArray | null
  while ((match = headingRegex.exec(html)) !== null) {
    const text = stripHtml(match[2] ?? '')
    const id = match[0].match(/\sid=["']([^"']+)["']/i)?.[1] ?? `section-${outline.length}`
    if (text) outline.push({ id, level: Number(match[1]), text })
  }

  return outline
}

function withHeadingIds(html: string): string {
  let index = 0
  return html.replace(/<h([2-4])([^>]*)>/gi, (match, level, attrs) => {
    if (String(attrs).includes('id=')) return match
    const id = `section-${index++}`
    return `<h${level}${attrs} id="${id}">`
  })
}

function countWordsFromHtml(html: string): number {
  return stripHtml(html).split(/\s+/).filter(Boolean).length
}

function isValidReadingTime(value: number | null | undefined): value is number {
  return typeof value === 'number' && Number.isFinite(value) && value >= 1
}

export default function ArticlePreviewPage() {
  const { projectId, articleId } = useParams<{ projectId: string; articleId: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [article, setArticle] = useState<EditorArticle | null>(null)
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading')

  useEffect(() => {
    if (!projectId || !articleId) return
    getEditorArticle(projectId, articleId)
      .then((data) => { setArticle(data); setStatus('success') })
      .catch(() => setStatus('error'))
  }, [projectId, articleId])

  if (status === 'loading') return <LoadingState />
  if (status === 'error' || !article) {
    return <ErrorState message="Impossible de charger l'article." onRetry={() => {
      setStatus('loading')
      if (projectId && articleId) {
        getEditorArticle(projectId, articleId)
          .then((data) => { setArticle(data); setStatus('success') })
          .catch(() => setStatus('error'))
      }
    }} />
  }

  const faqItems = parseFaqItems(article.faq_json)
  const renderedContent = article.content ? withHeadingIds(renderContent(article.content)) : ''
  const outline = buildOutline(renderedContent)
  const wordCount = article.word_count > 0 ? article.word_count : countWordsFromHtml(renderedContent)
  const readingTime = isValidReadingTime(article.reading_time_minutes)
    ? article.reading_time_minutes
    : (wordCount > 0 ? Math.max(1, Math.ceil(wordCount / 200)) : null)
  const authorName = article.author_name?.trim() || user?.name || '—'

  return (
    <div className="mx-auto max-w-[1034px]">
      <div className="mb-6 flex items-center justify-between">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-[14px] text-secondary transition-colors hover:text-primary"
        >
          <ArrowLeft size={14} />
          Retour
        </button>
        <Button
          icon={<Pencil size={14} />}
          size="sm"
          onClick={() => navigate(`/projects/${projectId}/articles/${articleId}/edit`)}
        >
          Editer
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,760px)_250px]">
        <article className="min-w-0">
          <div className="mb-8">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <StatusBadge status={article.status} />
              <span className="text-[12px] text-tertiary">
                Mis a jour le {formatDate(article.updated_at)}
              </span>
              <span className="text-[12px] text-tertiary">·</span>
              <span className="text-[12px] text-tertiary">Auteur : {authorName}</span>
              <span className="text-[12px] text-tertiary">·</span>
              <span className="text-[12px] text-tertiary">
                {readingTime ? `${readingTime} min de lecture` : 'Temps de lecture —'}
              </span>
            </div>
            <p className="mb-4 max-w-[680px] text-[15px] leading-relaxed text-secondary">
              {article.meta_description?.trim() || 'Meta description —'}
            </p>
            <h1 id="article-title" className="mb-5 max-w-[760px] text-[32px] font-bold leading-tight text-primary [overflow-wrap:anywhere]">
              {article.title}
            </h1>
            {article.cover_image_url && (
              <img
                src={article.cover_image_url}
                alt=""
                className="mb-8 aspect-[16/7] w-full rounded-[14px] object-cover"
              />
            )}
          </div>

          {article.content ? (
            <div
              className="max-w-[760px] text-[16px] leading-[1.78] text-primary [&_a]:text-accent [&_a]:underline [&_a]:underline-offset-2 [&_blockquote]:my-6 [&_blockquote]:rounded-r-[10px] [&_blockquote]:border-l-4 [&_blockquote]:border-accent [&_blockquote]:bg-accent/5 [&_blockquote]:px-4 [&_blockquote]:py-3 [&_blockquote]:text-secondary [&_blockquote]:italic [&_code]:rounded-[5px] [&_code]:bg-surface-soft [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[14px] [&_code]:text-primary [&_em]:italic [&_h1]:mb-4 [&_h1]:mt-7 [&_h1]:text-[26px] [&_h1]:font-bold [&_h1]:leading-tight [&_h2]:mb-3 [&_h2]:mt-8 [&_h2]:text-[22px] [&_h2]:font-semibold [&_h2]:leading-snug [&_h3]:mb-2.5 [&_h3]:mt-6 [&_h3]:text-[18px] [&_h3]:font-semibold [&_h3]:leading-snug [&_h4]:mb-2 [&_h4]:mt-5 [&_h4]:text-[16px] [&_h4]:font-semibold [&_hr]:my-8 [&_hr]:border-border [&_img]:my-7 [&_img]:max-w-full [&_img]:rounded-[14px] [&_img]:object-cover [&_li]:my-0.5 [&_li]:leading-[1.55] [&_li_p]:my-0 [&_ol]:my-5 [&_ol]:list-decimal [&_ol]:pl-9 [&_p]:my-4 [&_pre]:my-6 [&_pre]:overflow-x-auto [&_pre]:rounded-[12px] [&_pre]:bg-[#111318] [&_pre]:p-4 [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_pre_code]:text-[14px] [&_pre_code]:text-white [&_strong]:font-semibold [&_table]:my-7 [&_table]:w-full [&_table]:border-collapse [&_table]:overflow-hidden [&_table]:rounded-[12px] [&_td]:border [&_td]:border-border [&_td]:px-2 [&_td]:py-1 [&_td]:leading-tight [&_td_p]:my-0 [&_th]:border [&_th]:border-border [&_th]:bg-surface-soft [&_th]:px-2 [&_th]:py-1 [&_th]:text-left [&_th]:font-semibold [&_th]:leading-tight [&_th_p]:my-0 [&_u]:underline [&_ul]:my-5 [&_ul]:list-disc [&_ul]:pl-9 [&_ul[data-type='taskList']]:list-none [&_ul[data-type='taskList']]:pl-0 [&_ul[data-type='taskList']_li]:flex [&_ul[data-type='taskList']_li]:gap-2"
              dangerouslySetInnerHTML={{ __html: renderedContent }}
            />
          ) : (
            <div className="flex flex-col items-center gap-2 py-16 text-center">
              <p className="text-[15px] text-tertiary">Aucun contenu redige pour l'instant.</p>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => navigate(`/projects/${projectId}/articles/${articleId}/edit`)}
              >
                Commencer la redaction
              </Button>
            </div>
          )}

          {faqItems.length > 0 && (
            <section className="mt-10 border-t border-border pt-6">
              <h2 className="mb-4 text-[20px] font-semibold text-primary">FAQ</h2>
              <div className="flex flex-col gap-3">
                {faqItems.map((item, index) => (
                  <div key={index} className="rounded-[12px] border border-border bg-surface p-4">
                    <h3 className="text-[15px] font-semibold text-primary">{item.question}</h3>
                    <p className="mt-2 text-[15px] leading-relaxed text-secondary">{item.answer}</p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </article>

        <aside className="lg:sticky lg:top-4 lg:self-start">
          <div className="rounded-[14px] border border-border bg-surface p-4">
            <p className="mb-3 text-[12px] font-semibold uppercase tracking-wide text-tertiary">Plan</p>
            <nav className="flex flex-col gap-1.5">
              {outline.length > 0 ? (
                outline.map((item) => (
                  <a
                    key={item.id}
                    href={`#${item.id}`}
                    className={`text-[12px] leading-snug text-secondary [overflow-wrap:anywhere] hover:text-primary ${item.level === 3 ? 'pl-3' : item.level === 4 ? 'pl-6' : ''}`}
                  >
                    {item.text}
                  </a>
                ))
              ) : (
                <span className="text-[12px] text-tertiary">Aucun sous-titre.</span>
              )}
            </nav>
          </div>
        </aside>
      </div>
    </div>
  )
}
