import { api, ApiError } from './client'

export type ArticleComment = {
  id: string
  article_id: string
  author_id: string
  author_name: string
  text: string
  selected_text?: string | null
  resolved: boolean
  created_at: string
  updated_at: string
}

const indexKey = 'ideas-studio:local-comments:index'

function commentsKey(articleId: string) {
  return `ideas-studio:local-comments:${articleId}`
}

function shouldUseLocalFallback(error: unknown) {
  if (error instanceof ApiError) {
    return error.status === 404 || error.status === 405 || error.status === 501
  }
  return error instanceof TypeError
}

function readJson<T>(key: string, fallback: T): T {
  if (typeof window === 'undefined') return fallback
  try {
    const raw = window.localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

function writeJson<T>(key: string, value: T) {
  if (typeof window === 'undefined') return
  window.localStorage.setItem(key, JSON.stringify(value))
}

function readLocalComments(articleId: string) {
  return readJson<ArticleComment[]>(commentsKey(articleId), [])
}

function writeLocalComments(articleId: string, comments: ArticleComment[]) {
  writeJson(commentsKey(articleId), comments)
  const index = readJson<Record<string, string>>(indexKey, {})
  for (const comment of comments) index[comment.id] = articleId
  writeJson(indexKey, index)
}

function findLocalArticleId(commentId: string) {
  return readJson<Record<string, string>>(indexKey, {})[commentId] ?? null
}

function localId() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return `local-${crypto.randomUUID()}`
  }
  return `local-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export async function listComments(articleId: string): Promise<ArticleComment[]> {
  try {
    return await api.get<ArticleComment[]>(`/articles/${articleId}/comments`)
  } catch (error) {
    if (shouldUseLocalFallback(error)) return readLocalComments(articleId)
    throw error
  }
}

export async function createComment(
  articleId: string,
  text: string,
  selectedText?: string,
): Promise<ArticleComment> {
  try {
    if (!selectedText) return await api.post<ArticleComment>(`/articles/${articleId}/comments`, { text })

    try {
      return await api.post<ArticleComment>(`/articles/${articleId}/comments`, {
        text,
        selected_text: selectedText,
      })
    } catch (error) {
      if (shouldUseLocalFallback(error)) throw error
      return await api.post<ArticleComment>(`/articles/${articleId}/comments`, {
        text: `Sur: "${selectedText.slice(0, 160)}"\n\n${text}`,
      })
    }
  } catch (error) {
    if (!shouldUseLocalFallback(error)) throw error

    const now = new Date().toISOString()
    const comment: ArticleComment = {
      id: localId(),
      article_id: articleId,
      author_id: 'local',
      author_name: 'Vous',
      text,
      selected_text: selectedText ?? null,
      resolved: false,
      created_at: now,
      updated_at: now,
    }
    writeLocalComments(articleId, [comment, ...readLocalComments(articleId)])
    return comment
  }
}

export async function resolveComment(commentId: string, resolved: boolean): Promise<ArticleComment> {
  try {
    return await api.patch<ArticleComment>(`/comments/${commentId}`, { resolved })
  } catch (error) {
    if (!shouldUseLocalFallback(error)) throw error

    const articleId = findLocalArticleId(commentId)
    if (!articleId) throw error
    const now = new Date().toISOString()
    const comments = readLocalComments(articleId).map((comment) =>
      comment.id === commentId
        ? {
            ...comment,
            resolved,
            updated_at: now,
          }
        : comment
    )
    writeLocalComments(articleId, comments)
    const updated = comments.find((comment) => comment.id === commentId)
    if (!updated) throw error
    return updated
  }
}

export async function deleteComment(commentId: string): Promise<void> {
  try {
    await api.delete(`/comments/${commentId}`)
  } catch (error) {
    if (!shouldUseLocalFallback(error)) throw error

    const articleId = findLocalArticleId(commentId)
    if (!articleId) throw error
    writeLocalComments(
      articleId,
      readLocalComments(articleId).filter((comment) => comment.id !== commentId),
    )
    const index = readJson<Record<string, string>>(indexKey, {})
    delete index[commentId]
    writeJson(indexKey, index)
  }
}
