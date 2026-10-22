export type ChatRole = 'user' | 'assistant'

export interface ChatMessage {
  role: ChatRole
  content: string
}

/**
 * mode 由后端给出：'llm' 表示模型生成，'database' 表示直接查营养库，
 * 'placeholder' 表示 Python AI 服务不可用时的降级回复。
 * 前端只按值透传与展示，不写死判断结果。
 */
export interface AssistantReply {
  reply: string
  mode: string
  suggestions: string[]
}