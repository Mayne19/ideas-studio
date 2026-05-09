import { api } from './client'

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

export function listComments(articleId: string): Promise<ArticleComment[]> {
  return api.get<ArticleComment[]>(`/articles/${articleId}/comments`)
}

export async function createComment(
  articleId: string,
  text: string,
  selectedText?: string,
): Promise<ArticleComment> {
  if (!selectedText) return api.post<ArticleComment>(`/articles/${articleId}/comments`, { text })

  try {
    return await api.post<ArticleComment>(`/articles/${articleId}/comments`, {
      text,
      selected_text: selectedText,
    })
  } catch {
    return api.post<ArticleComment>(`/articles/${articleId}/comments`, {
      text: `Sur: "${selectedText.slice(0, 160)}"\n\n${text}`,
    })
  }
}

export function resolveComment(commentId: string, resolved: boolean): Promise<ArticleComment> {
  return api.patch<ArticleComment>(`/comments/${commentId}`, { resolved })
}

export function deleteComment(commentId: string): Promise<void> {
  return api.delete(`/comments/${commentId}`)
}
