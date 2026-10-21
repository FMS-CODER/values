import { requestJson } from '@/services/http'
import type { AssistantReply, ChatMessage } from '@/types/assistant'

/** 后端对 history 的硬上限 */
const MAX_HISTORY = 20

/**
 * 发送一条对话消息。
 * history 在前端先截到最近 20 条：后端超过 20 条会直接 400 拒绝整条请求，
 * 聊得久一点就突然发不出去，体验上很难理解。
 */
export function sendChatMessage(message: string, history: ChatMessage[]): Promise<AssistantReply> {
  return requestJson<AssistantReply>('/api/assistant/chat', 'POST', {
    message,
    history: history.slice(-MAX_HISTORY),
  })
}