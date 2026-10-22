import { request, requestJson } from '@/services/http'
import type {
  AssistantReply,
  ChatMessage,
  ConversationSummary,
  MessageRecord,
  PageResult,
} from '@/types/assistant'

/** 后端对 history 的硬上限 */
const MAX_HISTORY = 20

/**
 * 发送一条对话消息。
 * 有 conversationId 时由后端读取数据库中的历史；history 仍保留给旧接口兜底。
 */
export function sendChatMessage(
  message: string,
  history: ChatMessage[],
  conversationId?: number,
): Promise<AssistantReply> {
  return requestJson<AssistantReply>('/api/assistant/chat', 'POST', {
    message,
    history: history.slice(-MAX_HISTORY),
    conversationId: conversationId ?? null,
  })
}

export function listConversations(
  page = 1,
  size = 20,
): Promise<PageResult<ConversationSummary>> {
  return request<PageResult<ConversationSummary>>(
    `/api/assistant/conversations?page=${page}&size=${size}`,
  )
}

export function createConversation(title?: string): Promise<ConversationSummary> {
  return requestJson<ConversationSummary>('/api/assistant/conversations', 'POST', {
    title: title ?? null,
  })
}

export function deleteConversation(id: number): Promise<void> {
  return requestJson<void>(`/api/assistant/conversations/${id}`, 'DELETE')
}

export function listMessages(
  conversationId: number,
  page = 1,
  size = 50,
): Promise<PageResult<MessageRecord>> {
  return request<PageResult<MessageRecord>>(
    `/api/assistant/conversations/${conversationId}/messages?page=${page}&size=${size}`,
  )
}