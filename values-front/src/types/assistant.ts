export type ChatRole = 'user' | 'assistant'

export interface ChatMessage {
  role: ChatRole
  content: string
}

/**
 * mode 由后端给出：当前固定为 'placeholder'，表示 AI 服务（LangGraph）尚未接入。
 * 前端只按值透传与展示，不写死判断结果，接入真实模型后后端换值即可。
 */
export interface AssistantReply {
  reply: string
  mode: string
  suggestions: string[]
}