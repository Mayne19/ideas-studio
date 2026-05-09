import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Pencil } from 'lucide-react'
import { getEditorArticle } from '@/api/editor'
import type { EditorArticle } from '@/types'
import Button from '@/components/ui/Button'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import StatusBadge from '@/components/ui/StatusBadge'
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

function buildOutline(html: string, title: string): OutlineItem[] {
  const outline: OutlineItem[] = []
  if (title.trim()) outline.push({ id: 'article-title', level: 1, text: title.trim() })

  const headingRegex = /<h([2-4])[^>]*>([\s\S]*?)<\/h\1>/gi
  let match: RegExpExecArray | null
  while ((match = headingRegex.exec(html)) !== null) {
    const text = stripHtml(match[2] ?? '')
    if (text) outline.push({ id: `section-${outline.length}`, level: Number(match[1]), text })
  }

  return outline
}

function withHeadingIds(html: string): string {
  let index = 1
  return html.replace(/<h([2-4])([^>]*)>/gi, (match, level, attrs) => {
    if (String(attrs).includes('id=')) return match
    const id = `section-${index++}`
    return `<h${level}${attrs} id="${id}">`
  })
}

export default function ArticlePreviewPage() {
  const { projectId, articleId } = useParams<{ projectId: string; articleId: string }>()
  const navigate = useNavigate()
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

  const faqItems = Array.isArray(article.faq_json) ? (article.faq_json as FaqItem[]) : []
  const renderedContent = article.content ? withHeadingIds(renderContent(article.content)) : ''
  const outline = buildOutline(renderedContent, article.title)

  return (
    <div className="mx-auto max-w-6xl">
      <div className="mb-6 flex items-center justify-between">
        <button
          onClick={() => navigate(-1)}
          className="flex items-center gap-1.5 text-[13px] text-secondary transition-colors hover:text-primary"
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

      <div className="grid gap-6 lg:grid-cols-[240px_minmax(0,1fr)]">
        <aside className="lg:sticky lg:top-4 lg:self-start">
          <div className="rounded-[14px] border border-border bg-surface p-4">
            <p className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-tertiary">Plan</p>
            <nav className="flex flex-col gap-1.5">
              {outline.map((item) => (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  className={`truncate text-[12px] text-secondary hover:text-primary ${item.level === 3 ? 'pl-3' : item.level === 4 ? 'pl-6' : ''}`}
                >
                  {item.text}
                </a>
              ))}
            </nav>
          </div>
        </aside>

        <article className="min-w-0">
          <div className="mb-8">
            <div className="mb-3 flex items-center gap-2">
              <StatusBadge status={article.status} />
              <span className="text-[12px] text-tertiary">
                Mis a jour le {formatDate(article.updated_at)}
              </span>
            </div>
            {article.cover_image_url && (
              <img
                src={article.cover_image_url}
                alt=""
                className="mb-6 h-48 w-full rounded-[14px] object-cover"
              />
            )}
            <h1 id="article-title" className="mb-3 text-[28px] font-bold leading-tight tracking-tight text-primary">
              {article.title}
            </h1>
          </div>

          {article.content ? (
            <div
              className="prose prose-sm max-w-none text-[15px] leading-relaxed text-primary [&_a]:text-accent [&_blockquote]:border-l-4 [&_blockquote]:border-accent [&_blockquote]:pl-4 [&_blockquote]:text-secondary [&_h1]:text-[24px] [&_h1]:font-bold [&_h2]:text-[20px] [&_h2]:font-semibold [&_h3]:text-[17px] [&_h3]:font-semibold [&_li]:my-1 [&_ol]:my-3 [&_p]:my-3 [&_strong]:font-semibold [&_ul]:my-3"
              dangerouslySetInnerHTML={{ __html: renderedContent }}
            />
          ) : (
            <div className="flex flex-col items-center gap-2 py-16 text-center">
              <p className="text-[14px] text-tertiary">Aucun contenu redige pour l'instant.</p>
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
                    <p className="mt-2 text-[14px] leading-relaxed text-secondary">{item.answer}</p>
                  </div>
                ))}
              </div>
            </section>
          )}
        </article>
      </div>
    </div>
  )
}
