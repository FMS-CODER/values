export type ChatRole = 'user' | 'assistant'

export interface ChatMessage {
  role: ChatRole
  content: string
}

export interface Citation {
  documentId: string
  title: string
  source: string
  url: string
  snippet: string
  score: number
  kind: string
  reviewStatus: string
  version: string
}

/**
 * mode：llm=模型生成，database=营养库直答，rag=知识库引用，placeholder=服务降级。
 */
export interface AssistantReply {
  reply: string
  mode: string
  suggestions: string[]
  citations: Citation[]
  conversationId: number | null
  assistantMessageId: number | null
  intent: string
}

export interface ConversationSummary {
  id: number
  title: string
  createdAt: string
  updatedAt: string
}

export interface MessageRecord {
  id: number
  role: ChatRole
  content: string
  citations: Citation[]
  mode: string | null
  status: string
  createdAt: string
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  size: number
  totalPages: number
}