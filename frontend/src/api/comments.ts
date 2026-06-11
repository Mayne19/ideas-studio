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

export async function listComments(articleId: string): Promise<ArticleComment[]> {
  return await api.get<ArticleComment[]>(`/articles/${articleId}/comments`)
}

export async function createComment(
  articleId: string,
  text: string,
  selectedText?: string,
): Promise<ArticleComment> {
  if (!selectedText) {
    return await api.post<ArticleComment>(`/articles/${articleId}/comments`, { text })
  }
  return await api.post<ArticleComment>(`/articles/${articleId}/comments`, {
    text,
    selected_text: selectedText,
  })
}

export async function resolveComment(articleId: string, commentId: string, resolved: boolean): Promise<ArticleComment> {
  return await api.patch<ArticleComment>(`/articles/${articleId}/comments/${commentId}`, { resolved })
}

export async function deleteComment(articleId: string, commentId: string): Promise<void> {
  await api.delete(`/articles/${articleId}/comments/${commentId}`)
}
