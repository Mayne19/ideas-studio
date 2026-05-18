import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams, useBlocker } from 'react-router-dom'
import { useEditor, EditorContent } from '@tiptap/react'
import { Mark, mergeAttributes } from '@tiptap/core'
import StarterKit from '@tiptap/starter-kit'
import UnderlineExtension from '@tiptap/extension-underline'
import LinkExtension from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import TaskList from '@tiptap/extension-task-list'
import TaskItem from '@tiptap/extension-task-item'
import { Table } from '@tiptap/extension-table'
import { TableRow } from '@tiptap/extension-table-row'
import { TableHeader } from '@tiptap/extension-table-header'
import { TableCell } from '@tiptap/extension-table-cell'
import { CalloutExtension } from '@/lib/tiptap/CalloutExtension'
import { EditorImageExtension } from '@/lib/tiptap/EditorImageExtension'
import {
  Eye, BarChart2, Settings, History, Loader2, RefreshCw,
  AlertCircle, MessageCircle, ChevronDown, ChevronUp, Plus, Trash2,
  BookOpen, Type, Check, Send, Undo2, Redo2, PencilLine,
} from 'lucide-react'
import { getEditorArticle, autosaveArticle } from '@/api/editor'
import { listCategories } from '@/api/categories'
import { listCalloutTemplates } from '@/api/callouts'
import { listMembers } from '@/api/members'
import {
  createComment,
  deleteComment,
  listComments,
  resolveComment,
  type ArticleComment,
} from '@/api/comments'
import {
  publishArticle, promoteArticle, unpublishArticle, markReadyArticle, archiveArticle, scheduleArticle,
  type PromoteResponse,
} from '@/api/articles'
import { ApiError } from '@/api/client'
import type { EditorArticle, Category, ProjectMember, SeoAnalysis, ReadyCheck, CalloutTemplate } from '@/types'
import EditorToolbar from '@/components/editor/EditorToolbar'
import AutosaveIndicator from '@/components/editor/AutosaveIndicator'
import SeoPanel from '@/components/editor/SeoPanel'
import MediaPanel from '@/components/editor/MediaPanel'
import VersionsPanel from '@/components/editor/VersionsPanel'
import CommentsPanel from '@/components/editor/CommentsPanel'
import LoadingState from '@/components/ui/LoadingState'
import ErrorState from '@/components/ui/ErrorState'
import StatusBadge from '@/components/ui/StatusBadge'
import { useAuth } from '@/context/AuthContext'
import { formatDate } from '@/utils/format'

// ─── Types ────────────────────────────────────────────────────────────────────

export type MetaFields = {
  title: string
  slug: string
  excerpt: string
  meta_title: string
  meta_description: string
  keyword: string
  category_id: string
}

type FaqItem = { question: string; answer: string }
type ViewMode = 'read' | 'edit' | 'comment'
type RightTab = 'publish' | 'analyse' | 'versions'
type PublishMode = 'now' | 'schedule'
type CommentAnchor = { text: string; top: number; left: number; from: number; to: number }
type PersistedSnapshot = {
  title: string
  slug: string
  excerpt: string
  keyword: string
  meta_title: string
  meta_description: string
  category_id: string
  cover_image_url: string
  content: string
  faq_json: string | null
  author_name: string | null
  reading_time_minutes: number | null
}

const GENERATING_STATUSES: string[] = ['writing_requested', 'writing_in_progress']
const PUBLISHABLE_STATUSES = ['draft', 'outline_ready', 'writing_requested', 'writing_in_progress', 'draft_ready', 'review_needed', 'correction_needed', 'ready_to_publish', 'scheduled', 'update_recommended']

const RIGHT_TABS: { key: RightTab; label: string; icon: React.ReactNode }[] = [
  { key: 'publish',  label: 'Publication', icon: <Settings size={13} /> },
  { key: 'analyse',  label: 'Analyse',     icon: <BarChart2 size={13} /> },
  { key: 'versions', label: 'Versions',    icon: <History size={13} /> },
]

type AutosaveStatus = 'idle' | 'saving' | 'saved' | 'error'

const EMPTY_META: MetaFields = {
  title: '', slug: '', excerpt: '', meta_title: '', meta_description: '', keyword: '', category_id: '',
}

const CommentMark = Mark.create({
  name: 'commentMark',
  addAttributes() {
    return {
      id: {
        default: null,
        parseHTML: (element) => element.getAttribute('data-comment-id'),
        renderHTML: (attributes) => ({ 'data-comment-id': attributes.id }),
      },
    }
  },
  parseHTML() {
    return [{ tag: 'span[data-comment-id]' }]
  },
  renderHTML({ HTMLAttributes }) {
    return ['span', mergeAttributes(HTMLAttributes, { class: 'comment-mark' }), 0]
  },
})

// ─── Small helpers ─────────────────────────────────────────────────────────────

function Field({
  label, children, hint,
}: { label: string; children: React.ReactNode; hint?: string }) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-[11px] font-medium text-secondary">{label}</label>
      {children}
      {hint && <p className="text-[10px] text-tertiary">{hint}</p>}
    </div>
  )
}

const INPUT = 'w-full rounded-[8px] border border-border bg-surface px-2.5 py-1.5 text-[12px] text-primary placeholder:text-tertiary focus:outline-none focus:ring-1 focus:ring-accent/50 focus:border-accent/60 transition-colors'

function translateError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 409) return "Action impossible dans l'état actuel."
    if (err.status === 403) return 'Permission insuffisante.'
    return err.message || `Erreur ${err.status}`
  }
  return 'Une erreur inattendue est survenue.'
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

function serializeFaqItems(items: FaqItem[]) {
  const filled = items.filter((item) => item.question.trim() || item.answer.trim())
  return filled.length > 0 ? JSON.stringify(filled) : null
}

function normalizeOptionalText(value: string | null | undefined): string | null {
  const trimmed = value?.trim() ?? ''
  return trimmed ? trimmed : null
}

function normalizeReadingTime(value: number | null | undefined): number | null {
  return typeof value === 'number' && Number.isFinite(value) && value >= 1
    ? Math.round(value)
    : null
}

function isEffectivelyEmptyHtml(value: string | null | undefined): boolean {
  const html = value ?? ''
  const text = html
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/\u00a0/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  return text === ''
}

function buildPersistedSnapshot({
  content,
  meta,
  coverImageUrl,
  faqItems,
  authorName,
  readingTimeMinutes,
}: {
  content: string
  meta: MetaFields
  coverImageUrl: string
  faqItems: FaqItem[]
  authorName: string
  readingTimeMinutes: number | null
}): PersistedSnapshot {
  return {
    title: meta.title,
    slug: meta.slug,
    excerpt: meta.excerpt,
    keyword: meta.keyword,
    meta_title: meta.meta_title,
    meta_description: meta.meta_description,
    category_id: meta.category_id,
    cover_image_url: coverImageUrl,
    content,
    faq_json: serializeFaqItems(faqItems),
    author_name: normalizeOptionalText(authorName),
    reading_time_minutes: normalizeReadingTime(readingTimeMinutes),
  }
}

function snapshotsEqual(a: PersistedSnapshot | null, b: PersistedSnapshot): boolean {
  if (!a) return false
  return JSON.stringify(a) === JSON.stringify(b)
}

function buildPublishedSnapshot(article: EditorArticle | null): PersistedSnapshot | null {
  if (!article || article.status !== 'published') return null
  const hasPublishedFields = article.published_content !== null || article.published_title !== null || article.published_excerpt !== null
  if (!hasPublishedFields) {
    return buildPersistedSnapshot({
      content: article.content ?? '',
      meta: {
        title: article.title ?? '',
        slug: article.slug ?? '',
        excerpt: article.excerpt ?? '',
        keyword: article.keyword ?? '',
        meta_title: article.meta_title ?? '',
        meta_description: article.meta_description ?? '',
        category_id: article.category_id ?? '',
      },
      coverImageUrl: article.cover_image_url ?? '',
      faqItems: parseFaqItems(article.faq_json),
      authorName: article.author_name ?? '',
      readingTimeMinutes: article.reading_time_minutes,
    })
  }
  return {
    title: article.published_title ?? '',
    slug: article.slug ?? '',
    excerpt: article.published_excerpt ?? '',
    keyword: article.keyword ?? '',
    meta_title: article.meta_title ?? '',
    meta_description: article.published_meta_description ?? '',
    category_id: article.category_id ?? '',
    cover_image_url: article.published_cover_image_url ?? '',
    content: article.published_content ?? '',
    faq_json: article.published_faq_json as string | null ?? null,
    author_name: normalizeOptionalText(article.author_name),
    reading_time_minutes: normalizeReadingTime(article.reading_time_minutes),
  }
}

// ─── Main component ────────────────────────────────────────────────────────────

export default function ArticleEditorPage() {
  const { projectId, articleId } = useParams<{ projectId: string; articleId: string }>()
  const navigate = useNavigate()
  const { user } = useAuth()

  // Load state
  const [article, setArticle] = useState<EditorArticle | null>(null)
  const [loadStatus, setLoadStatus] = useState<'loading' | 'success' | 'error'>('loading')
  const [isGenerating, setIsGenerating] = useState(false)
  const [generationTimedOut, setGenerationTimedOut] = useState(false)

  // Editor UI state
  const [viewMode, setViewMode] = useState<ViewMode>('edit')
  const [rightTab, setRightTab] = useState<RightTab>('publish')
  const [autosaveStatus, setAutosaveStatus] = useState<AutosaveStatus>('idle')
  const [latestSeoAnalysis, setLatestSeoAnalysis] = useState<SeoAnalysis | null>(null)
  const [latestReadyCheck, setLatestReadyCheck] = useState<ReadyCheck | null>(null)

  // Content fields
  const [metaFields, setMetaFields] = useState<MetaFields>(EMPTY_META)
  const [coverImageUrl, setCoverImageUrl] = useState('')
  const [categories, setCategories] = useState<Category[]>([])
  const [calloutTemplates, setCalloutTemplates] = useState<CalloutTemplate[]>([])
  const [members, setMembers] = useState<ProjectMember[]>([])
  const [selectedAuthorId, setSelectedAuthorId] = useState('')
  const [manualAuthorName, setManualAuthorName] = useState('')
  const [manualReadingTime, setManualReadingTime] = useState<number | null>(null)
  const [persistedSnapshot, setPersistedSnapshot] = useState<PersistedSnapshot | null>(null)
  const [lastPromotedSnapshot, setLastPromotedSnapshot] = useState<PersistedSnapshot | null>(null)
  const [faqItems, setFaqItems] = useState<FaqItem[]>([])
  const [faqOpen, setFaqOpen] = useState(false)

  // Publication actions
  const [actionError, setActionError] = useState('')
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [publishMode, setPublishMode] = useState<PublishMode>('now')
  const [scheduleDate, setScheduleDate] = useState('')
  const [scheduleTime, setScheduleTime] = useState('')

  // Inline comment state
  const [commentAnchor, setCommentAnchor] = useState<CommentAnchor | null>(null)
  const [selectedCommentId, setSelectedCommentId] = useState<string | null>(null)
  const [selectedCommentPopup, setSelectedCommentPopup] = useState<{ top: number; left: number } | null>(null)
  const [comments, setComments] = useState<ArticleComment[]>([])
  const [commentsLoading, setCommentsLoading] = useState(true)
  const [commentInput, setCommentInput] = useState('')
  const [sendingComment, setSendingComment] = useState(false)
  const [commentRefreshKey, setCommentRefreshKey] = useState(0)
  const commentPopoverRef = useRef<HTMLDivElement>(null)

  // Refs (stable references for closures)
  const metaRef = useRef<MetaFields>(EMPTY_META)
  const coverRef = useRef('')
  const faqRef = useRef<FaqItem[]>([])
  const authorNameRef = useRef('')
  const readingTimeRef = useRef<number | null>(null)
  const autosaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const pendingSaveRef = useRef(false)
  const titleRef = useRef<HTMLTextAreaElement>(null)
  const isHydratingEditorRef = useRef(false)
  const lastHydratedArticleIdRef = useRef<string | null>(null)
  const lastHydratedContentRef = useRef<string | null>(null)
  const slugManuallyEditedRef = useRef(false)

  // Navigation blocker
  const blocker = useBlocker(
    ({ currentLocation, nextLocation }) =>
      (pendingSaveRef.current || autosaveStatus === 'saving') &&
      currentLocation.pathname !== nextLocation.pathname
  )

  // ─── TipTap editor ──────────────────────────────────────────────────────────

  const editor = useEditor({
    extensions: [
      StarterKit,
      UnderlineExtension,
      LinkExtension.configure({ openOnClick: false }),
      EditorImageExtension,
      Placeholder.configure({ placeholder: 'Commencez à rédiger votre article…' }),
      TaskList,
      TaskItem.configure({ nested: true }),
      Table.configure({
        resizable: true,
        HTMLAttributes: { class: 'editor-table' },
      }),
      TableRow,
      TableHeader,
      TableCell,
      CalloutExtension.configure({
        HTMLAttributes: { 'data-block-type': 'callout' },
      }),
      CommentMark,
    ],
    content: '',
    editable: true,
    editorProps: {
      attributes: {
        class: 'tiptap-content min-h-[58vh] px-10 pb-10 pt-0 [&>*:first-child]:mt-0',
      },
      handleClick: (_view, _pos, event) => {
        const target = event.target as HTMLElement
        const marked = target.closest('[data-comment-id]') as HTMLElement | null
        if (!marked) return false
        const commentId = marked.getAttribute('data-comment-id')
        if (!commentId) return false
        setSelectedCommentId(commentId)
        setSelectedCommentPopup({
          top: Math.max(12, Math.min(event.clientY + 12, window.innerHeight - 220)),
          left: Math.max(12, Math.min(event.clientX + 12, window.innerWidth - 292)),
        })
        return false
      },
    },
    onUpdate: ({ editor: e }) => {
      if (isHydratingEditorRef.current) return
      scheduleAutosave(e.getHTML())
    },
  })

  useEffect(() => {
    if (editor) editor.setEditable(viewMode === 'edit')
  }, [editor, viewMode])

  const activeRightTab: RightTab = rightTab

  // ─── Autosave ───────────────────────────────────────────────────────────────

  const scheduleAutosave = useCallback((html: string) => {
    if (autosaveTimer.current) clearTimeout(autosaveTimer.current)
    pendingSaveRef.current = true
    const pid = projectId
    const aid = articleId
    autosaveTimer.current = setTimeout(() => {
      if (!pid || !aid) return
      setAutosaveStatus('saving')
      autosaveArticle(pid, aid, {
        content: html,
        title: metaRef.current.title || undefined,
        slug: metaRef.current.slug || undefined,
        excerpt: metaRef.current.excerpt || undefined,
        keyword: normalizeOptionalText(metaRef.current.keyword),
        meta_title: metaRef.current.meta_title || undefined,
        meta_description: metaRef.current.meta_description || undefined,
        cover_image_url: normalizeOptionalText(coverRef.current),
        category_id: normalizeOptionalText(metaRef.current.category_id),
        faq_json: serializeFaqItems(faqRef.current),
        author_name: normalizeOptionalText(authorNameRef.current),
        reading_time_minutes: normalizeReadingTime(readingTimeRef.current),
      })
        .then((response) => {
          pendingSaveRef.current = false
          setPersistedSnapshot(buildPersistedSnapshot({
            content: html,
            meta: metaRef.current,
            coverImageUrl: coverRef.current,
            faqItems: faqRef.current,
            authorName: authorNameRef.current,
            readingTimeMinutes: readingTimeRef.current,
          }))
          setArticle((prev) => prev ? {
            ...prev,
            title: metaRef.current.title,
            slug: metaRef.current.slug,
            excerpt: metaRef.current.excerpt,
            keyword: normalizeOptionalText(metaRef.current.keyword),
            meta_title: normalizeOptionalText(metaRef.current.meta_title),
            meta_description: normalizeOptionalText(metaRef.current.meta_description),
            category_id: normalizeOptionalText(metaRef.current.category_id),
            cover_image_url: normalizeOptionalText(coverRef.current),
            content: html,
            faq_json: serializeFaqItems(faqRef.current),
            author_name: normalizeOptionalText(authorNameRef.current),
            reading_time_minutes: normalizeReadingTime(readingTimeRef.current),
            word_count: response.word_count,
            updated_at: response.updated_at,
          } : prev)
          setAutosaveStatus('saved')
          setTimeout(() => setAutosaveStatus('idle'), 3000)
        })
        .catch(() => {
          pendingSaveRef.current = false
          setAutosaveStatus('error')
        })
    }, 2000)
  }, [projectId, articleId])

  const handleSaveNow = useCallback(async () => {
    if (autosaveTimer.current) clearTimeout(autosaveTimer.current)
    const pid = projectId
    const aid = articleId
    if (!pid || !aid) return
    setAutosaveStatus('saving')
    try {
      const content = editor?.getHTML() ?? ''
      const response = await autosaveArticle(pid, aid, {
        content,
        title: metaRef.current.title || undefined,
        slug: metaRef.current.slug || undefined,
        excerpt: metaRef.current.excerpt || undefined,
        keyword: normalizeOptionalText(metaRef.current.keyword),
        meta_title: metaRef.current.meta_title || undefined,
        meta_description: metaRef.current.meta_description || undefined,
        cover_image_url: normalizeOptionalText(coverRef.current),
        category_id: normalizeOptionalText(metaRef.current.category_id),
        faq_json: serializeFaqItems(faqRef.current),
        author_name: normalizeOptionalText(authorNameRef.current),
        reading_time_minutes: normalizeReadingTime(readingTimeRef.current),
      })
      pendingSaveRef.current = false
      setPersistedSnapshot(buildPersistedSnapshot({
        content,
        meta: metaRef.current,
        coverImageUrl: coverRef.current,
        faqItems: faqRef.current,
        authorName: authorNameRef.current,
        readingTimeMinutes: readingTimeRef.current,
      }))
      setArticle((prev) => prev ? {
        ...prev,
        title: metaRef.current.title,
        slug: metaRef.current.slug,
        excerpt: metaRef.current.excerpt,
        keyword: normalizeOptionalText(metaRef.current.keyword),
        meta_title: normalizeOptionalText(metaRef.current.meta_title),
        meta_description: normalizeOptionalText(metaRef.current.meta_description),
        category_id: normalizeOptionalText(metaRef.current.category_id),
        cover_image_url: normalizeOptionalText(coverRef.current),
        content,
        faq_json: serializeFaqItems(faqRef.current),
        author_name: normalizeOptionalText(authorNameRef.current),
        reading_time_minutes: normalizeReadingTime(readingTimeRef.current),
        word_count: response.word_count,
        updated_at: response.updated_at,
      } : prev)
      setAutosaveStatus('saved')
      setTimeout(() => setAutosaveStatus('idle'), 3000)
    } catch {
      pendingSaveRef.current = false
      setAutosaveStatus('error')
    }
  }, [articleId, editor, projectId])

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
        e.preventDefault()
        void handleSaveNow()
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [handleSaveNow])

  useEffect(() => {
    function handleBeforeUnload(e: BeforeUnloadEvent) {
      if (pendingSaveRef.current || autosaveStatus === 'saving') e.preventDefault()
    }
    window.addEventListener('beforeunload', handleBeforeUnload)
    return () => window.removeEventListener('beforeunload', handleBeforeUnload)
  }, [autosaveStatus])

  // ─── Data loading ────────────────────────────────────────────────────────────

  useEffect(() => {
    if (!projectId || !articleId) return
    Promise.all([
      getEditorArticle(projectId, articleId),
      listCategories(projectId),
      listCalloutTemplates(projectId).catch(() => [] as CalloutTemplate[]),
      listMembers(projectId).catch(() => [] as ProjectMember[]),
    ])
      .then(([art, cats, callouts, mems]) => {
        setCategories(cats)
        setCalloutTemplates(callouts)
        setMembers(mems)
        setLatestSeoAnalysis(null)
        setLatestReadyCheck(null)
        setSelectedAuthorId(mems.find((m) => m.user_id === user?.id)?.user_id ?? mems[0]?.user_id ?? '')
        setArticle(art)
        const meta: MetaFields = {
          title: art.title ?? '',
          slug: art.slug ?? '',
          excerpt: art.excerpt ?? '',
          meta_title: art.meta_title ?? '',
          meta_description: art.meta_description ?? '',
          keyword: art.keyword ?? '',
          category_id: art.category_id ?? '',
        }
        setMetaFields(meta)
        metaRef.current = meta
        slugManuallyEditedRef.current = false
        const cover = art.cover_image_url ?? ''
        setCoverImageUrl(cover)
        coverRef.current = cover
        const faq = parseFaqItems(art.faq_json)
        setFaqItems(faq)
        faqRef.current = faq
        setManualAuthorName(art.author_name ?? '')
        authorNameRef.current = art.author_name ?? ''
        setManualReadingTime(normalizeReadingTime(art.reading_time_minutes))
        readingTimeRef.current = normalizeReadingTime(art.reading_time_minutes)
        setPersistedSnapshot(buildPersistedSnapshot({
          content: art.content ?? '',
          meta,
          coverImageUrl: cover,
          faqItems: faq,
          authorName: art.author_name ?? '',
          readingTimeMinutes: art.reading_time_minutes,
        }))
        setLastPromotedSnapshot(buildPublishedSnapshot(art))
        setIsGenerating(GENERATING_STATUSES.includes(art.status))
        setLoadStatus('success')
      })
      .catch(() => setLoadStatus('error'))
  }, [projectId, articleId, user?.id])

  useEffect(() => {
    if (!editor || !article) return

    const incomingContent = article.content ?? ''
    const currentHtml = editor.getHTML()
    const currentArticleId = article.id
    const lastHydratedArticleId = lastHydratedArticleIdRef.current
    const lastHydratedContent = lastHydratedContentRef.current
    const articleChanged = lastHydratedArticleId !== currentArticleId
    const contentChangedSinceHydration = lastHydratedContent !== incomingContent
    const editorIsSafeToHydrate =
      articleChanged ||
      isEffectivelyEmptyHtml(currentHtml) ||
      currentHtml === (lastHydratedContent ?? '')

    if (!editorIsSafeToHydrate || (!contentChangedSinceHydration && !articleChanged)) return

    isHydratingEditorRef.current = true
    try {
      editor.commands.setContent(incomingContent, { emitUpdate: false })
    } finally {
      isHydratingEditorRef.current = false
    }
    lastHydratedArticleIdRef.current = currentArticleId
    lastHydratedContentRef.current = incomingContent
  }, [editor, article])

  useEffect(() => {
    if (!articleId) return
    let active = true
    Promise.resolve().then(() => { if (active) setCommentsLoading(true) })
    listComments(articleId)
      .then((items) => {
        if (active) setComments(items)
      })
      .catch(() => {
        if (active) setComments([])
      })
      .finally(() => {
        if (active) setCommentsLoading(false)
      })
    return () => { active = false }
  }, [articleId, commentRefreshKey])

  function handleCalloutTemplateCreated(template: CalloutTemplate) {
    setCalloutTemplates((current) => {
      if (current.some((item) => item.id === template.id)) return current
      return [...current, template]
    })
  }

  useEffect(() => {
    if (!selectedCommentId) return
    const stillVisible = comments.some((comment) => comment.id === selectedCommentId && !comment.resolved)
    if (!stillVisible) {
      Promise.resolve().then(() => {
        setSelectedCommentId(null)
        setSelectedCommentPopup(null)
      })
    }
  }, [comments, selectedCommentId])

  // ─── Generation polling ──────────────────────────────────────────────────────

  useEffect(() => {
    if (!isGenerating || !projectId || !articleId) return
    let count = 0
    const id = setInterval(async () => {
      count++
      if (count > 40) {
        clearInterval(id)
        setIsGenerating(false)
        setGenerationTimedOut(true)
        return
      }
      try {
        const art = await getEditorArticle(projectId, articleId)
        if (!GENERATING_STATUSES.includes(art.status)) {
          clearInterval(id)
          setIsGenerating(false)
          setGenerationTimedOut(false)
          setArticle(art)
          const m: MetaFields = {
            title: art.title ?? '', slug: art.slug ?? '', excerpt: art.excerpt ?? '',
            meta_title: art.meta_title ?? '', meta_description: art.meta_description ?? '',
            keyword: art.keyword ?? '', category_id: art.category_id ?? '',
          }
          setMetaFields(m)
          metaRef.current = m
          const cov = art.cover_image_url ?? ''
          setCoverImageUrl(cov)
          coverRef.current = cov
          const faq = parseFaqItems(art.faq_json)
          setFaqItems(faq)
          faqRef.current = faq
          setManualAuthorName(art.author_name ?? '')
          authorNameRef.current = art.author_name ?? ''
          setManualReadingTime(normalizeReadingTime(art.reading_time_minutes))
          readingTimeRef.current = normalizeReadingTime(art.reading_time_minutes)
          setPersistedSnapshot(buildPersistedSnapshot({
            content: art.content ?? '',
            meta: m,
            coverImageUrl: cov,
            faqItems: faq,
            authorName: art.author_name ?? '',
            readingTimeMinutes: art.reading_time_minutes,
          }))
          if (editor && art.content) editor.commands.setContent(art.content)
        }
      } catch { /* ignore poll errors */ }
    }, 3000)
    return () => clearInterval(id)
  }, [isGenerating, projectId, articleId, editor])

  async function handleRefreshGeneration() {
    if (!projectId || !articleId) return
    setGenerationTimedOut(false)
    try {
      const art = await getEditorArticle(projectId, articleId)
      if (GENERATING_STATUSES.includes(art.status)) {
        setIsGenerating(true)
      } else {
        setIsGenerating(false)
        setArticle(art)
        const m: MetaFields = {
          title: art.title ?? '', slug: art.slug ?? '', excerpt: art.excerpt ?? '',
          meta_title: art.meta_title ?? '', meta_description: art.meta_description ?? '',
          keyword: art.keyword ?? '', category_id: art.category_id ?? '',
        }
        setMetaFields(m)
        metaRef.current = m
        const cov = art.cover_image_url ?? ''
        setCoverImageUrl(cov)
        coverRef.current = cov
        const faq = parseFaqItems(art.faq_json)
        setFaqItems(faq)
        faqRef.current = faq
        setManualAuthorName(art.author_name ?? '')
        authorNameRef.current = art.author_name ?? ''
        setManualReadingTime(normalizeReadingTime(art.reading_time_minutes))
        readingTimeRef.current = normalizeReadingTime(art.reading_time_minutes)
        setPersistedSnapshot(buildPersistedSnapshot({
          content: art.content ?? '',
          meta: m,
          coverImageUrl: cov,
          faqItems: faq,
          authorName: art.author_name ?? '',
          readingTimeMinutes: art.reading_time_minutes,
        }))
        if (editor && art.content) editor.commands.setContent(art.content)
      }
    } catch { /* ignore */ }
  }

  // ─── Comment mode selection ──────────────────────────────────────────────────

  useEffect(() => {
    if (viewMode !== 'comment' || !editor) return

    function handleMouseUp(e: MouseEvent) {
      if (commentPopoverRef.current?.contains(e.target as Node)) return
      setSelectedCommentPopup(null)
      const sel = window.getSelection()
      if (!sel || sel.rangeCount === 0) { setCommentAnchor(null); return }
      const text = sel.toString().trim()
      if (!text) { setCommentAnchor(null); return }
      const rangeForPosition = sel.getRangeAt(0)
      let from = editor.state.selection.from
      let to = editor.state.selection.to
      try {
        from = editor.view.posAtDOM(rangeForPosition.startContainer, rangeForPosition.startOffset)
        to = editor.view.posAtDOM(rangeForPosition.endContainer, rangeForPosition.endOffset)
      } catch {
        // Keep the ProseMirror selection as fallback.
      }
      const start = Math.min(from, to)
      const end = Math.max(from, to)
      if (start === end) { setCommentAnchor(null); return }
      const range = rangeForPosition
      const rect = range.getBoundingClientRect()
      if (rect.width === 0 && rect.height === 0) { setCommentAnchor(null); return }
      const top = rect.bottom + 8
      const left = Math.max(8, Math.min(rect.left, window.innerWidth - 264))
      setCommentAnchor({ text, top, left, from: start, to: end })
      setCommentInput('')
    }

    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === 'Escape') { setCommentAnchor(null); setCommentInput('') }
    }

    document.addEventListener('mouseup', handleMouseUp)
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('mouseup', handleMouseUp)
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [viewMode, editor])

  // ─── Field change handlers ───────────────────────────────────────────────────

  function slugify(text: string): string {
    return text.toLowerCase().trim()
      .replace(/[^\w\s-]/g, '')
      .replace(/[\s_]+/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '') || 'item'
  }

  function handleMetaChange(name: keyof MetaFields, value: string) {
    const next = { ...metaRef.current, [name]: value }
    if (name === 'title' && !slugManuallyEditedRef.current && article && article.status !== 'published') {
      next.slug = slugify(value || 'item')
    }
    if (name === 'slug') {
      slugManuallyEditedRef.current = true
    }
    metaRef.current = next
    setMetaFields(next)
    if (name === 'title') setArticle((prev) => prev ? { ...prev, title: value, slug: next.slug } : prev)
    scheduleAutosave(editor?.getHTML() ?? '')
  }

  function handleCoverChange(url: string) {
    coverRef.current = url
    setCoverImageUrl(url)
    scheduleAutosave(editor?.getHTML() ?? '')
  }

  function handleAuthorNameChange(value: string) {
    authorNameRef.current = value
    setManualAuthorName(value)
    setArticle((prev) => prev ? { ...prev, author_name: normalizeOptionalText(value) } : prev)
    scheduleAutosave(editor?.getHTML() ?? '')
  }

  function handleReadingTimeChange(value: string) {
    const trimmed = value.trim()
    const nextValue = trimmed ? normalizeReadingTime(Number(trimmed)) : null
    readingTimeRef.current = nextValue
    setManualReadingTime(nextValue)
    setArticle((prev) => prev ? { ...prev, reading_time_minutes: nextValue } : prev)
    scheduleAutosave(editor?.getHTML() ?? '')
  }

  function handleTitleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    handleMetaChange('title', e.target.value)
    e.currentTarget.style.height = 'auto'
    e.currentTarget.style.height = `${e.currentTarget.scrollHeight}px`
  }

  useEffect(() => {
    const title = titleRef.current
    if (!title) return
    title.style.height = 'auto'
    title.style.height = `${title.scrollHeight}px`
  }, [metaFields.title])

  function handleFaqChange(index: number, field: keyof FaqItem, value: string) {
    const next = faqItems.map((item, i) => i === index ? { ...item, [field]: value } : item)
    setFaqItems(next)
    faqRef.current = next
    scheduleAutosave(editor?.getHTML() ?? '')
  }

  function handleFaqAdd() {
    const next = [...faqItems, { question: '', answer: '' }]
    setFaqItems(next)
    faqRef.current = next
    setFaqOpen(true)
    scheduleAutosave(editor?.getHTML() ?? '')
  }

  function handleFaqDelete(index: number) {
    const next = faqItems.filter((_, i) => i !== index)
    setFaqItems(next)
    faqRef.current = next
    scheduleAutosave(editor?.getHTML() ?? '')
  }

  // ─── Publication actions ─────────────────────────────────────────────────────

  async function doAction(key: string) {
    if (!projectId || !article) return
    setActionLoading(key)
    setActionError('')
    try {
      if (key === 'publish' || key === 'promote') {
        if (autosaveTimer.current) clearTimeout(autosaveTimer.current)
        const content = editor?.getHTML() ?? article.content ?? ''
        await autosaveArticle(projectId, article.id, {
          content,
          title: metaRef.current.title || undefined,
          slug: metaRef.current.slug || undefined,
          excerpt: metaRef.current.excerpt || undefined,
          keyword: normalizeOptionalText(metaRef.current.keyword),
          meta_title: metaRef.current.meta_title || undefined,
          meta_description: normalizeOptionalText(metaRef.current.meta_description),
          cover_image_url: normalizeOptionalText(coverRef.current),
          category_id: normalizeOptionalText(metaRef.current.category_id),
          faq_json: serializeFaqItems(faqRef.current),
          author_name: normalizeOptionalText(authorNameRef.current),
          reading_time_minutes: normalizeReadingTime(readingTimeRef.current),
        })
      }
      let updated: EditorArticle | undefined
      let revalidated: boolean | undefined
      if (key === 'publish') {
        const resp = await publishArticle(projectId, article.id)
        updated = resp as unknown as EditorArticle
        revalidated = (resp as { revalidated?: boolean }).revalidated
      } else if (key === 'unpublish') {
        updated = await unpublishArticle(projectId, article.id) as unknown as EditorArticle
      } else if (key === 'mark-ready') {
        updated = await markReadyArticle(projectId, article.id) as unknown as EditorArticle
      } else if (key === 'archive') {
        updated = await archiveArticle(projectId, article.id) as unknown as EditorArticle
      }
      if (updated) setArticle((prev) => ({ ...prev!, ...updated }))
      if (revalidated === false) {
        setActionError('Article publié, mais cache du site non revalidé.')
      }
    } catch (err) {
      setActionError(translateError(err))
    } finally {
      setActionLoading(null)
    }
  }

  async function handlePromote() {
    if (!projectId || !article) return
    setActionLoading('promote')
    setActionError('')
    try {
      if (autosaveTimer.current) clearTimeout(autosaveTimer.current)
      const content = editor?.getHTML() ?? article.content ?? ''
      await autosaveArticle(projectId, article.id, {
        content,
        title: metaRef.current.title || undefined,
        slug: metaRef.current.slug || undefined,
        excerpt: metaRef.current.excerpt || undefined,
        keyword: normalizeOptionalText(metaRef.current.keyword),
        meta_title: metaRef.current.meta_title || undefined,
        meta_description: normalizeOptionalText(metaRef.current.meta_description),
        cover_image_url: normalizeOptionalText(coverRef.current),
        category_id: normalizeOptionalText(metaRef.current.category_id),
        faq_json: serializeFaqItems(faqRef.current),
        author_name: normalizeOptionalText(authorNameRef.current),
        reading_time_minutes: normalizeReadingTime(readingTimeRef.current),
      })
      const updated: PromoteResponse = await promoteArticle(projectId, article.id)
      setArticle((prev) => prev ? {
        ...prev,
        ...updated,
        content: prev.content,
        title: prev.title,
        excerpt: prev.excerpt,
        meta_description: prev.meta_description,
        cover_image_url: prev.cover_image_url,
        faq_json: prev.faq_json,
        callouts_json: prev.callouts_json,
      } : prev)
      const promotedSnapshot = buildPersistedSnapshot({
        content,
        meta: metaFields,
        coverImageUrl: coverImageUrl,
        faqItems,
        authorName: manualAuthorName,
        readingTimeMinutes: manualReadingTime,
      })
      setPersistedSnapshot(promotedSnapshot)
      setLastPromotedSnapshot(promotedSnapshot)
      if (!updated.revalidated) {
        setActionError('Article mis à jour, mais cache du site non revalidé.')
      }
    } catch (err) {
      setActionError(translateError(err))
    } finally {
      setActionLoading(null)
    }
  }

  async function handleSchedule() {
    if (!projectId || !article || !scheduleDate || !scheduleTime) return
    setActionLoading('schedule')
    setActionError('')
    try {
      const iso = new Date(`${scheduleDate}T${scheduleTime}`).toISOString()
      const updated = await scheduleArticle(projectId, article.id, iso)
      setArticle((prev) => ({ ...prev!, ...updated }))
      setScheduleDate('')
      setScheduleTime('')
    } catch (err) {
      setActionError(translateError(err))
    } finally {
      setActionLoading(null)
    }
  }

  async function handleSendInlineComment() {
    if (!articleId || !commentAnchor || !commentInput.trim() || !editor) return
    setSendingComment(true)
    try {
      const comment = await createComment(articleId, commentInput.trim(), commentAnchor.text)
      editor.setEditable(true)
      editor
        .chain()
        .focus()
        .setTextSelection({ from: commentAnchor.from, to: commentAnchor.to })
        .setMark('commentMark', { id: comment.id })
        .run()
      editor.commands.setTextSelection(commentAnchor.to)
      editor.setEditable(viewMode === 'edit')
      scheduleAutosave(editor.getHTML())
      setComments((prev) => [comment, ...prev.filter((item) => item.id !== comment.id)])
      setSelectedCommentId(comment.id)
      setSelectedCommentPopup(null)
      setCommentAnchor(null)
      setCommentInput('')
      setCommentRefreshKey((k) => k + 1)
    } catch { /* ignore */ }
    finally {
      setSendingComment(false)
    }
  }

  function removeCommentMark(commentId: string) {
    if (!editor) return
    const markType = editor.schema.marks['commentMark']
    if (!markType) return

    let tr = editor.state.tr
    editor.state.doc.descendants((node, pos) => {
      if (!node.isText) return
      const hasComment = node.marks.some((mark) => mark.type === markType && mark.attrs['id'] === commentId)
      if (hasComment) tr = tr.removeMark(pos, pos + node.nodeSize, markType)
    })

    if (tr.docChanged) {
      editor.view.dispatch(tr)
      scheduleAutosave(editor.getHTML())
    }
  }

  async function handleResolveInlineComment(id: string, resolved = true) {
    const updated = await resolveComment(id, resolved)
    setComments((prev) => prev.map((comment) => comment.id === id ? updated : comment))
    if (resolved) {
      removeCommentMark(id)
      setSelectedCommentId(null)
      setSelectedCommentPopup(null)
    }
  }

  async function handleDeleteInlineComment(id: string) {
    await deleteComment(id)
    removeCommentMark(id)
    setComments((prev) => prev.filter((comment) => comment.id !== id))
    setSelectedCommentId(null)
    setSelectedCommentPopup(null)
  }

  // ─── Derived values ──────────────────────────────────────────────────────────

  const wordCount = editor
    ? editor.getText().split(/\s+/).filter(Boolean).length
    : (article?.word_count ?? 0)

  const calculatedReadingTime = Math.max(1, Math.ceil(wordCount / 200))
  const readingTime = normalizeReadingTime(manualReadingTime) ?? calculatedReadingTime
  const currentSnapshot = buildPersistedSnapshot({
    content: editor?.getHTML() ?? article?.content ?? '',
    meta: metaFields,
    coverImageUrl: coverImageUrl,
    faqItems,
    authorName: manualAuthorName,
    readingTimeMinutes: manualReadingTime,
  })
  const hasUnsavedChanges = !snapshotsEqual(persistedSnapshot, currentSnapshot)
  const showUpdateButton = article?.status === 'published' && (
    hasUnsavedChanges ||
    (lastPromotedSnapshot !== null && !snapshotsEqual(lastPromotedSnapshot, currentSnapshot))
  )

  const isEditable = viewMode === 'edit'
  const busy = actionLoading !== null
  const selectedComment = comments.find((comment) => comment.id === selectedCommentId) ?? null

  // ─── Loading / error ─────────────────────────────────────────────────────────

  if (loadStatus === 'loading') return <LoadingState />
  if (loadStatus === 'error' || !article) {
    return <ErrorState message="Impossible de charger l'article." onRetry={() => navigate(0)} />
  }

  // ─── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="flex h-full flex-col min-h-0">

      {/* Navigation blocker */}
      {blocker.state === 'blocked' && (
        <div className="flex items-center justify-between gap-3 bg-warning/8 border-b border-warning/20 px-4 py-2 shrink-0">
          <span className="text-[12px] text-warning">
            Sauvegarde en cours — quitter maintenant pourrait entraîner une perte de données.
          </span>
          <div className="flex items-center gap-2">
            <button onClick={() => blocker.reset?.()} className="rounded-[6px] px-2.5 py-1 text-[11px] font-medium text-warning hover:bg-warning/10">Rester</button>
            <button onClick={() => blocker.proceed?.()} className="rounded-[6px] px-2.5 py-1 text-[11px] font-medium text-danger hover:bg-danger/8">Quitter</button>
          </div>
        </div>
      )}

      {/* Generation overlay */}
      {(isGenerating || generationTimedOut) && (
        <div className="flex flex-1 items-center justify-center">
          <div className="flex flex-col items-center gap-4 text-center max-w-xs">
            <div className={`flex h-12 w-12 items-center justify-center rounded-[16px] ${generationTimedOut ? 'bg-danger/8' : 'bg-accent/10'}`}>
              {generationTimedOut
                ? <AlertCircle size={22} className="text-danger" />
                : <Loader2 size={22} className="animate-spin text-accent" />
              }
            </div>
            <div>
              <p className="text-[15px] font-medium text-primary">
                {generationTimedOut ? 'La génération prend plus de temps que prévu' : 'Génération en cours…'}
              </p>
              <p className="mt-1 text-[13px] text-secondary">
                {generationTimedOut
                  ? 'Cliquez sur Rafraîchir pour vérifier si le brouillon est disponible.'
                  : "L'IA rédige votre brouillon. La page se mettra à jour automatiquement."
                }
              </p>
            </div>
            <button
              onClick={handleRefreshGeneration}
              className={`flex items-center gap-1.5 rounded-[10px] px-4 py-2 text-[13px] font-medium transition-colors ${
                generationTimedOut ? 'bg-accent text-white hover:bg-accent/90' : 'bg-[#f0f0f2] text-secondary hover:bg-[#e5e5e7]'
              }`}
            >
              <RefreshCw size={13} />
              Rafraîchir
            </button>
            <button onClick={() => navigate(`/projects/${projectId}/ideas`)} className="text-[12px] text-tertiary hover:text-secondary transition-colors">
              ← Retour au pipeline d'idées
            </button>
          </div>
        </div>
      )}

      {/* 3-card layout */}
      {!isGenerating && !generationTimedOut && (
        <div className="grid min-h-0 flex-1 grid-cols-[56px_minmax(0,1fr)_300px] items-start gap-4 overflow-y-auto overflow-x-hidden p-4 max-xl:grid-cols-[52px_minmax(0,1fr)_280px]">

          {/* ── LEFT: Toolbar card ── */}
          <div className="sticky top-0 flex max-h-[calc(100vh-112px)] min-w-0 flex-col overflow-y-auto rounded-[14px] border border-border bg-surface">
            <EditorToolbar
              editor={editor}
              projectId={projectId}
              articleId={articleId}
              calloutTemplates={calloutTemplates}
              onCalloutTemplateCreated={handleCalloutTemplateCreated}
              disabled={viewMode !== 'edit'}
            />
          </div>

          {/* ── CENTER: Article card ── */}
          <div className={`flex min-w-0 flex-col overflow-hidden rounded-[14px] border border-border ${!isEditable ? 'bg-app' : 'bg-surface'}`}>

            {/* Internal bar */}
            <div className="flex items-center justify-between gap-2 px-4 py-2 border-b border-border shrink-0 bg-surface">
              {/* Left: back + autosave */}
              <div className="flex items-center gap-2 min-w-0">
                <div className="flex rounded-[10px] bg-[#f0f0f2] p-1">
                  {([
                    { mode: 'read' as ViewMode, label: 'Lecture', icon: <BookOpen size={12} /> },
                    { mode: 'edit' as ViewMode, label: 'Édition', icon: <PencilLine size={12} /> },
                    { mode: 'comment' as ViewMode, label: 'Commentaire', icon: <MessageCircle size={12} /> },
                  ]).map(({ mode, label, icon }) => (
                    <button
                      key={mode}
                      onClick={() => setViewMode(mode)}
                      className={`flex h-7 items-center gap-1.5 rounded-[7px] px-2.5 text-[11px] font-medium transition-all ${
                        viewMode === mode
                          ? 'bg-surface text-primary shadow-sm'
                          : 'text-secondary hover:text-primary'
                      }`}
                    >
                      {icon}
                      {label}
                    </button>
                  ))}
                </div>
                <span className="text-border text-[10px]">·</span>
                <span className="hidden text-[12px] text-secondary truncate max-w-[200px]">
                  {metaFields.title || article.title}
                </span>
                <AutosaveIndicator status={autosaveStatus} />
              </div>

              {/* Right: word count + preview + history */}
              <div className="flex items-center gap-1.5 shrink-0">
                <div className="hidden rounded-[8px] border border-border overflow-hidden">
                  {([
                    { mode: 'read'    as ViewMode, label: 'Lecture' },
                    { mode: 'edit'    as ViewMode, label: 'Édition' },
                    { mode: 'comment' as ViewMode, label: 'Commentaire', icon: <MessageCircle size={11} /> },
                  ]).map(({ mode, label, icon }) => (
                    <button
                      key={mode}
                      onClick={() => setViewMode(mode)}
                      className={`flex items-center gap-1 px-2.5 py-1 text-[11px] font-medium transition-colors ${
                        viewMode === mode
                          ? 'bg-accent text-white'
                          : 'text-secondary hover:text-primary hover:bg-[#f0f0f2]'
                      }`}
                    >
                      {icon}
                      {label}
                    </button>
                  ))}
                </div>

                <span className="flex items-center gap-1 text-[11px] text-tertiary px-1">
                  <Type size={10} />
                  {wordCount.toLocaleString('fr-FR')}
                </span>

                <button
                  onClick={() => navigate(`/projects/${projectId}/articles/${articleId}/preview`)}
                  className="flex items-center gap-1 text-[11px] text-secondary hover:text-primary transition-colors rounded-[6px] px-2 py-1 hover:bg-[#f0f0f2]"
                >
                  <Eye size={12} />
                  Prévisualiser
                </button>
                <button
                  onClick={() => editor?.chain().focus().undo().run()}
                  disabled={!editor?.can().undo()}
                  className="flex h-7 w-7 items-center justify-center rounded-[7px] text-secondary transition-colors hover:bg-[#f0f0f2] hover:text-primary disabled:opacity-35"
                  title="Annuler"
                >
                  <Undo2 size={13} />
                </button>
                <button
                  onClick={() => editor?.chain().focus().redo().run()}
                  disabled={!editor?.can().redo()}
                  className="flex h-7 w-7 items-center justify-center rounded-[7px] text-secondary transition-colors hover:bg-[#f0f0f2] hover:text-primary disabled:opacity-35"
                  title="Refaire"
                >
                  <Redo2 size={13} />
                </button>
              </div>
            </div>

            {/* Scrollable content area */}
            <div className="flex-1 overflow-y-auto">

              {/* Comment mode banner */}
              {viewMode === 'comment' && (
                <div className="flex items-center gap-2 px-10 py-2 bg-accent/5 border-b border-accent/20">
                  <MessageCircle size={13} className="text-accent shrink-0" />
                  <span className="text-[12px] text-accent">
                    Mode commentaire — sélectionnez du texte pour ajouter un commentaire
                  </span>
                </div>
              )}

              {/* Title */}
              <div className="px-10 pt-7 pb-2">
                <textarea
                  ref={titleRef}
                  value={metaFields.title}
                  onChange={handleTitleInput}
                  readOnly={!isEditable}
                  placeholder="Titre de l'article…"
                  rows={1}
                  className={`block w-full max-w-full resize-none overflow-hidden whitespace-normal break-words bg-transparent text-[28px] font-bold leading-tight text-primary outline-none placeholder:text-tertiary/40 [overflow-wrap:anywhere] ${!isEditable ? 'cursor-default' : ''}`}
                />
              </div>

              {/* TipTap editor */}
              <EditorContent
                editor={editor}
                className={`${!isEditable ? 'cursor-default select-text' : ''}`}
              />

              {/* FAQ section */}
              <div className="px-10 py-4 border-t border-border/60 mt-4">
                <button
                  onClick={() => setFaqOpen((v) => !v)}
                  className="flex items-center gap-2 w-full text-left"
                >
                  <span className="text-[12px] font-semibold text-secondary uppercase tracking-wide flex-1">
                    FAQ {faqItems.length > 0 && `(${faqItems.length})`}
                  </span>
                  {faqOpen ? <ChevronUp size={14} className="text-tertiary" /> : <ChevronDown size={14} className="text-tertiary" />}
                </button>

                {faqOpen && (
                  <div className="mt-3 flex flex-col gap-3">
                    {faqItems.map((item, i) => (
                      <div key={i} className="rounded-[10px] border border-border bg-[#f9f9fb] p-3 flex flex-col gap-2">
                        <div className="flex items-start gap-2">
                          <input
                            type="text"
                            value={item.question}
                            onChange={(e) => handleFaqChange(i, 'question', e.target.value)}
                            placeholder="Question…"
                            className="flex-1 bg-transparent text-[13px] font-semibold text-primary outline-none placeholder:text-tertiary"
                          />
                          <button onClick={() => handleFaqDelete(i)} className="shrink-0 text-tertiary hover:text-danger transition-colors mt-0.5">
                            <Trash2 size={13} />
                          </button>
                        </div>
                        <textarea
                          rows={2}
                          value={item.answer}
                          onChange={(e) => handleFaqChange(i, 'answer', e.target.value)}
                          placeholder="Réponse…"
                          className="w-full bg-white rounded-[8px] border border-border px-2.5 py-1.5 text-[13px] text-primary placeholder:text-tertiary resize-none outline-none focus:ring-1 focus:ring-accent/50 focus:border-accent/60 transition-colors"
                        />
                      </div>
                    ))}
                    <button
                      onClick={handleFaqAdd}
                      className="flex items-center gap-1.5 text-[12px] text-accent hover:underline"
                    >
                      <Plus size={13} />
                      Ajouter FAQ
                    </button>
                  </div>
                )}

                {!faqOpen && faqItems.length === 0 && (
                  <button
                    onClick={handleFaqAdd}
                    className="mt-2 flex items-center gap-1.5 text-[12px] text-tertiary hover:text-accent transition-colors"
                  >
                    <Plus size={13} />
                    Ajouter une FAQ
                  </button>
                )}
              </div>
            </div>

            {/* Footer: word count + reading time */}
            <div className="flex items-center justify-end gap-3 px-10 py-2 border-t border-border/60 bg-surface shrink-0">
              <span className="flex items-center gap-1 text-[11px] text-tertiary">
                <BookOpen size={10} />
                {readingTime} min de lecture
              </span>
              <span className="text-[11px] text-tertiary">{wordCount.toLocaleString('fr-FR')} mots</span>
            </div>
          </div>

          {/* ── RIGHT: Panel card ── */}
          <div className="sticky top-0 flex max-h-[calc(100vh-112px)] min-w-0 flex-col overflow-hidden rounded-[14px] border border-border bg-surface">

            {/* Tab bar */}
            <div className="flex border-b border-border shrink-0">
              {RIGHT_TABS.map((tab) => (
                <button
                  key={tab.key}
                  onClick={() => setRightTab(tab.key)}
                  className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-[11px] font-medium border-b-2 transition-colors ${
                    activeRightTab === tab.key
                      ? 'border-accent text-accent'
                      : 'border-transparent text-tertiary hover:text-secondary'
                  }`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab content */}
            <div className="flex-1 overflow-y-auto">

              {/* ── Publication tab ── */}
              {activeRightTab === 'publish' && (
                <div className="flex flex-col divide-y divide-border">

                  {/* 1. Catégorie */}
                  <div className="p-3 flex flex-col gap-2">
                    {categories.length > 0 && (
                      <Field label="Catégorie">
                        <select
                          value={metaFields.category_id}
                          onChange={(e) => handleMetaChange('category_id', e.target.value)}
                          className={INPUT}
                        >
                          <option value="">— Aucune —</option>
                          {categories.map((cat) => (
                            <option key={cat.id} value={cat.id}>{cat.name}</option>
                          ))}
                        </select>
                      </Field>
                    )}
                    <Field label="Mot-clé principal" hint="Pour l'analyse SEO">
                      <input
                        type="text"
                        value={metaFields.keyword}
                        onChange={(e) => handleMetaChange('keyword', e.target.value)}
                        className={INPUT}
                        placeholder="ex: marketing digital"
                      />
                    </Field>
                  </div>

                  {/* 2. Slug */}
                  <div className="p-3">
                    <Field label="Slug" hint="URL de l'article">
                      <div className="flex gap-1.5">
                        <input
                          type="text"
                          value={metaFields.slug}
                          onChange={(e) => handleMetaChange('slug', e.target.value)}
                          className={INPUT}
                          placeholder="/mon-article"
                        />
                        <button
                          type="button"
                          onClick={() => {
                            const s = slugify(metaFields.title || 'item')
                            handleMetaChange('slug', s)
                            slugManuallyEditedRef.current = false
                          }}
                          className="shrink-0 rounded-[8px] border border-border bg-surface px-2 text-[11px] text-secondary hover:bg-[#f0f0f2] hover:text-primary transition-colors"
                          title="Régénérer depuis le titre"
                        >
                          ↻
                        </button>
                      </div>
                    </Field>
                  </div>

                  {/* 3. Statut */}
                  <div className="p-3 flex items-center justify-between">
                    <span className="text-[11px] font-medium text-secondary">Statut</span>
                    <StatusBadge status={article.status} />
                  </div>

                  {/* 3. Couverture */}
                  <div className="p-3 flex flex-col gap-2">
                    <span className="text-[11px] font-medium text-secondary">Image de couverture</span>
                    <MediaPanel coverImageUrl={coverImageUrl} onChange={handleCoverChange} projectId={projectId!} />
                  </div>

                  {/* 4. Meta description */}
                  <div className="p-3">
                    <Field label="Meta description">
                      <textarea
                        rows={3}
                        value={metaFields.meta_description}
                        onChange={(e) => handleMetaChange('meta_description', e.target.value)}
                        className={`${INPUT} resize-none`}
                        placeholder="Description pour les moteurs de recherche…"
                      />
                    </Field>
                  </div>

                  {/* 5. Auteur (public) + Temps de lecture */}
                  <div className="p-3 flex flex-col gap-2">
                    <div className="flex items-center justify-between text-[12px]">
                      <span className="text-secondary">Auteur (publication)</span>
                      <input
                        type="text"
                        value={manualAuthorName}
                        onChange={(e) => handleAuthorNameChange(e.target.value)}
                        placeholder="Nom d'auteur"
                        className="max-w-[190px] bg-transparent text-right text-primary text-[12px] border-none outline-none placeholder:text-tertiary"
                      />
                    </div>
                    <div className="flex items-center justify-between text-[12px]">
                      <span className="text-secondary">Responsable</span>
                      {members.length > 0 ? (
                        <select
                          value={selectedAuthorId}
                          onChange={(e) => setSelectedAuthorId(e.target.value)}
                          className="max-w-[190px] bg-transparent text-right text-primary text-[12px] border-none outline-none cursor-pointer"
                        >
                          {members.map((m) => (
                            <option key={m.user_id} value={m.user_id}>
                              {m.user_name ?? m.user_email ?? m.user_id}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <span className="text-primary">{user?.name ?? '—'}</span>
                      )}
                    </div>
                    <div className="flex items-center justify-between text-[12px]">
                      <span className="text-secondary">Temps de lecture (min)</span>
                      <input
                        type="number"
                        min={1}
                        value={manualReadingTime ?? ''}
                        placeholder={String(calculatedReadingTime)}
                        onChange={(e) => handleReadingTimeChange(e.target.value)}
                        className="w-16 rounded-[7px] border border-border bg-surface px-2 py-1 text-right text-[12px] text-primary outline-none focus:border-accent/60 focus:ring-1 focus:ring-accent/40"
                      />
                    </div>
                  </div>

                  {/* 6. Dates */}
                  {(article.published_at || article.updated_at) && (
                    <div className="p-3 flex flex-col gap-1.5">
                      {article.published_at && (
                        <div className="flex items-center justify-between text-[12px]">
                          <span className="text-secondary">Publié le</span>
                          <span className="text-primary">{formatDate(article.published_at)}</span>
                        </div>
                      )}
                      {article.status === 'published' && (
                        <div className="flex items-center justify-between text-[12px]">
                          <span className="text-secondary">Mis à jour</span>
                          <span className="text-primary">{formatDate(article.updated_at)}</span>
                        </div>
                      )}
                      {article.scheduled_at && article.status === 'scheduled' && (
                        <div className="flex items-center justify-between text-[12px]">
                          <span className="text-secondary">Programmé le</span>
                          <span className="text-primary">{formatDate(article.scheduled_at)}</span>
                        </div>
                      )}
                    </div>
                  )}

                  {/* 7. Publier maintenant / Programmer */}
                  {article.status === 'published' ? (
                    <div className="p-3 flex flex-col gap-2">
                      {showUpdateButton ? (
                        <button
                          onClick={() => void handlePromote()}
                          disabled={busy || actionLoading === 'promote'}
                          className="w-full rounded-[8px] bg-accent py-2 text-[12px] font-medium text-white hover:bg-accent/90 disabled:opacity-40 transition-colors"
                        >
                          {actionLoading === 'promote' ? <Loader2 size={12} className="animate-spin inline mr-1" /> : null}
                          Mettre à jour
                        </button>
                      ) : (
                        <div className="w-full rounded-[8px] border border-success/20 bg-success/8 py-2 text-center text-[12px] font-medium text-success">
                          Publié
                        </div>
                      )}
                      <button
                        onClick={() => doAction('unpublish')}
                        disabled={busy}
                        className="w-full rounded-[8px] border border-border py-2 text-[12px] font-medium text-secondary hover:bg-[#f0f0f2] transition-colors disabled:opacity-40"
                      >
                        Dépublier
                      </button>
                      {showUpdateButton && (
                        <p className="text-[10px] text-tertiary text-center">
                          Les modifications locales seront sauvegardees sans depublier l'article.
                        </p>
                      )}
                    </div>
                  ) : article.status !== 'archived' ? (
                    <div className="p-3 flex flex-col gap-3">
                      {/* Mode toggle */}
                      <div className="flex rounded-[8px] border border-border overflow-hidden">
                        <button
                          onClick={() => setPublishMode('now')}
                          className={`flex-1 py-1.5 text-[11px] font-medium transition-colors ${publishMode === 'now' ? 'bg-accent text-white' : 'text-secondary hover:bg-[#f0f0f2]'}`}
                        >
                          Maintenant
                        </button>
                        <button
                          onClick={() => setPublishMode('schedule')}
                          className={`flex-1 py-1.5 text-[11px] font-medium transition-colors ${publishMode === 'schedule' ? 'bg-accent text-white' : 'text-secondary hover:bg-[#f0f0f2]'}`}
                        >
                          Programmer
                        </button>
                      </div>

                      {publishMode === 'now' && (
                        <div className="flex flex-col gap-1.5">
                          <button
                            onClick={() => doAction('publish')}
                            disabled={busy || !PUBLISHABLE_STATUSES.includes(article.status)}
                            className="w-full rounded-[8px] bg-accent py-2 text-[12px] font-medium text-white hover:bg-accent/90 disabled:opacity-40 transition-colors"
                          >
                            {actionLoading === 'publish' ? <Loader2 size={12} className="animate-spin inline mr-1" /> : null}
                            Publier maintenant
                          </button>
                          {!PUBLISHABLE_STATUSES.includes(article.status) && (
                            <p className="text-[10px] text-tertiary text-center">
                              Marquez l'article comme prêt avant de publier.
                            </p>
                          )}
                        </div>
                      )}

                      {publishMode === 'schedule' && (
                        <div className="flex flex-col gap-2 rounded-[10px] bg-[#f9f9fb] border border-border p-3">
                          <Field label="Date">
                            <input
                              type="date"
                              value={scheduleDate}
                              onChange={(e) => setScheduleDate(e.target.value)}
                              className={INPUT}
                            />
                          </Field>
                          <Field label="Heure">
                            <input
                              type="time"
                              value={scheduleTime}
                              onChange={(e) => setScheduleTime(e.target.value)}
                              className={INPUT}
                            />
                          </Field>
                          <button
                            onClick={handleSchedule}
                            disabled={!scheduleDate || !scheduleTime || busy}
                            className="w-full rounded-[8px] bg-accent py-1.5 text-[11px] font-medium text-white hover:bg-accent/90 disabled:opacity-40 transition-colors"
                          >
                            {actionLoading === 'schedule' ? '…' : 'Programmer la publication'}
                          </button>
                        </div>
                      )}
                    </div>
                  ) : null}

                  {/* 8. Comments */}
                  <div className="p-3">
                    <p className="text-[11px] font-medium text-secondary mb-2 flex items-center gap-1.5">
                      <MessageCircle size={12} className="text-tertiary" />
                      Commentaires éditoriaux
                    </p>
                    {selectedCommentId && (
                      <p className="mb-2 rounded-[7px] bg-accent/6 px-2 py-1 text-[10px] text-accent">
                        Commentaire selectionne dans le texte.
                      </p>
                    )}
                    <CommentsPanel
                      articleId={articleId!}
                      comments={comments}
                      loading={commentsLoading}
                      selectedCommentId={selectedCommentId}
                      onResolve={handleResolveInlineComment}
                      onDelete={handleDeleteInlineComment}
                      onSelect={(comment) => {
                        setSelectedCommentId(comment.id)
                        setSelectedCommentPopup(null)
                      }}
                    />
                  </div>

                  {/* Error */}
                  {actionError && (
                    <div className="mx-3 mb-2 flex items-start gap-1.5 rounded-[8px] bg-danger/5 border border-danger/20 px-2.5 py-2 text-[11px] text-danger">
                      <AlertCircle size={11} className="mt-0.5 shrink-0" />
                      <span>{actionError}</span>
                    </div>
                  )}

                  {/* 9. Secondary actions */}
                  <div className="p-3 flex flex-col gap-1.5">
                    <button
                      onClick={handleSaveNow}
                      disabled={busy}
                      className="w-full flex items-center justify-center gap-1.5 rounded-[8px] border border-border py-2 text-[12px] font-medium text-secondary hover:bg-[#f0f0f2] transition-colors disabled:opacity-40"
                    >
                      {autosaveStatus === 'saved' ? <Check size={13} className="text-success" /> : null}
                      Sauvegarder
                    </button>
                    {!['ready_to_publish', 'published', 'archived'].includes(article.status) && (
                      <button
                        onClick={() => doAction('mark-ready')}
                        disabled={busy}
                        className="w-full rounded-[8px] border border-border py-2 text-[12px] font-medium text-secondary hover:bg-[#f0f0f2] transition-colors disabled:opacity-40"
                      >
                        {actionLoading === 'mark-ready' ? <Loader2 size={12} className="animate-spin inline mr-1" /> : null}
                        Marquer prêt
                      </button>
                    )}
                    {article.status !== 'archived' && (
                      <button
                        onClick={() => doAction('archive')}
                        disabled={busy}
                        className="w-full rounded-[8px] py-2 text-[12px] font-medium text-danger/70 hover:text-danger hover:bg-danger/5 transition-colors disabled:opacity-40"
                      >
                        Archiver
                      </button>
                    )}
                  </div>
                </div>
              )}

              {/* ── Analyse tab ── */}
              {activeRightTab === 'analyse' && (
                <div className="p-3">
                  <SeoPanel
                    article={{ ...article, title: metaFields.title }}
                    projectId={projectId!}
                    onBeforeAnalyze={handleSaveNow}
                    initialAnalysis={latestSeoAnalysis}
                    initialReadiness={latestReadyCheck}
                    onAnalysisUpdate={(analysis) => {
                      setLatestSeoAnalysis(analysis)
                      setArticle((prev) => prev ? {
                        ...prev,
                        seo_score: analysis.seo_score,
                        readability_score: analysis.readability_score,
                        quality_score: analysis.quality_score,
                        eeat_score: analysis.eeat_score,
                        readiness_status: analysis.readiness_status,
                        latest_analysis: {
                          seo_score: analysis.seo_score,
                          readability_score: analysis.readability_score,
                          quality_score: analysis.quality_score,
                          eeat_score: analysis.eeat_score,
                          readiness_status: analysis.readiness_status,
                          created_at: analysis.created_at,
                        },
                      } : prev)
                    }}
                    onReadinessUpdate={setLatestReadyCheck}
                    onExpertReviewUpdate={(review) => {
                      setArticle((prev) => prev ? {
                        ...prev,
                        seo_review_json: review,
                      } : prev)
                    }}
                  />
                </div>
              )}

              {/* ── Versions tab ── */}
              {activeRightTab === 'versions' && (
                <div className="p-3">
                  <VersionsPanel
                    projectId={projectId!}
                    articleId={articleId!}
                    members={members}
                    onRestore={(restored) => {
                      setArticle(restored)
                      const meta: MetaFields = {
                        title: restored.title ?? '', slug: restored.slug ?? '', excerpt: restored.excerpt ?? '',
                        meta_title: restored.meta_title ?? '', meta_description: restored.meta_description ?? '',
                        keyword: restored.keyword ?? '', category_id: restored.category_id ?? '',
                      }
                      setMetaFields(meta)
                      metaRef.current = meta
                      const cover = restored.cover_image_url ?? ''
                      setCoverImageUrl(cover)
                      coverRef.current = cover
                      const faq = parseFaqItems(restored.faq_json)
                      setFaqItems(faq)
                      faqRef.current = faq
                      setManualAuthorName(restored.author_name ?? '')
                      authorNameRef.current = restored.author_name ?? ''
                      setManualReadingTime(normalizeReadingTime(restored.reading_time_minutes))
                      readingTimeRef.current = normalizeReadingTime(restored.reading_time_minutes)
                      setPersistedSnapshot(buildPersistedSnapshot({
                        content: restored.content ?? '',
                        meta,
                        coverImageUrl: cover,
                        faqItems: faq,
                        authorName: restored.author_name ?? '',
                        readingTimeMinutes: restored.reading_time_minutes,
                      }))
                      if (editor && restored.content) editor.commands.setContent(restored.content)
                      setRightTab('publish')
                    }}
                  />
                </div>
              )}

            </div>
          </div>

        </div>
      )}

      {/* Inline comment popover (fixed overlay) */}
      {commentAnchor && viewMode === 'comment' && (
        <div
          ref={commentPopoverRef}
          style={{ top: commentAnchor.top, left: commentAnchor.left, boxShadow: '0 20px 60px rgba(0,0,0,0.14)' }}
          className="fixed z-50 w-[256px] rounded-[14px] border border-border bg-surface p-3 flex flex-col gap-2"
        >
          <p className="text-[10px] text-secondary leading-snug">
            Sur :{' '}
            <span className="italic text-primary">
              «{commentAnchor.text.slice(0, 80)}{commentAnchor.text.length > 80 ? '…' : ''}»
            </span>
          </p>
          <textarea
            autoFocus
            rows={3}
            value={commentInput}
            onChange={(e) => setCommentInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); handleSendInlineComment() }
            }}
            placeholder="Votre commentaire…"
            className="w-full rounded-[8px] border border-border bg-[#f9f9fb] px-2.5 py-1.5 text-[12px] text-primary placeholder:text-tertiary resize-none focus:outline-none focus:ring-1 focus:ring-accent/50 focus:border-accent/60 transition-colors"
          />
          <div className="flex gap-1.5">
            <button
              onClick={() => { setCommentAnchor(null); setCommentInput('') }}
              className="flex-1 rounded-[8px] border border-border py-1.5 text-[11px] text-secondary hover:bg-[#e5e5e7] transition-colors"
            >
              Annuler
            </button>
            <button
              onClick={handleSendInlineComment}
              disabled={!commentInput.trim() || sendingComment}
              className="flex-1 flex items-center justify-center gap-1 rounded-[8px] bg-accent py-1.5 text-[11px] font-medium text-white hover:bg-accent/90 disabled:opacity-40 transition-colors"
            >
              {sendingComment ? <Loader2 size={11} className="animate-spin" /> : <Send size={11} />}
              Commenter
            </button>
          </div>
        </div>
      )}

      {selectedComment && selectedCommentPopup && (
        <div
          style={{ top: selectedCommentPopup.top, left: selectedCommentPopup.left, boxShadow: '0 20px 60px rgba(0,0,0,0.14)' }}
          className="fixed z-50 w-[280px] rounded-[14px] border border-border bg-surface p-3"
        >
          {selectedComment.selected_text && (
            <p className="mb-2 rounded-[8px] bg-accent/6 px-2 py-1 text-[10px] leading-snug text-secondary">
              «{selectedComment.selected_text.slice(0, 110)}{selectedComment.selected_text.length > 110 ? '…' : ''}»
            </p>
          )}
          <p className="text-[12px] leading-snug text-primary">{selectedComment.text}</p>
          <div className="mt-3 flex gap-1.5">
            <button
              onClick={() => void handleResolveInlineComment(selectedComment.id, true)}
              className="flex flex-1 items-center justify-center gap-1 rounded-[8px] bg-success/10 py-1.5 text-[11px] font-medium text-success transition-colors hover:bg-success/15"
            >
              <Check size={11} />
              Valider
            </button>
            <button
              onClick={() => void handleDeleteInlineComment(selectedComment.id)}
              className="flex flex-1 items-center justify-center gap-1 rounded-[8px] border border-border py-1.5 text-[11px] font-medium text-danger transition-colors hover:bg-danger/5"
            >
              <Trash2 size={11} />
              Supprimer
            </button>
          </div>
        </div>
      )}

    </div>
  )
}
