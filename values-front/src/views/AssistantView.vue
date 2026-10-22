<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import {
  Apple,
  BookOpen,
  Bot,
  ChevronRight,
  CircleAlert,
  ExternalLink,
  Flame,
  History,
  Leaf,
  LoaderCircle,
  MessageCircle,
  MessageSquareText,
  MessagesSquare,
  Plus,
  RotateCcw,
  Salad,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  UtensilsCrossed,
  X,
} from 'lucide-vue-next'
import {
  createConversation,
  deleteConversation,
  listConversations,
  listMessages,
  sendChatMessage,
} from '@/services/assistant'
import type {
  ChatMessage,
  Citation,
  ConversationSummary,
  MessageRecord,
} from '@/types/assistant'

const MAX_MESSAGE_LENGTH = 1000
const CURRENT_CONVERSATION_KEY = 'values:assistant-conversation'

const QUICK_CARDS = [
  { title: '食物营养分析', prompt: '西兰花有哪些营养亮点？', icon: Salad, tone: 'green' },
  { title: '营养成分对比', prompt: '鸡胸肉和牛里脊的营养有什么区别？', icon: UtensilsCrossed, tone: 'coral' },
  { title: '了解营养素', prompt: '维生素 C 有哪些营养作用？', icon: Apple, tone: 'orange' },
  { title: '寻找高蛋白食物', prompt: '哪些食物的蛋白质含量较高？', icon: Search, tone: 'blue' },
]

const HOT_TOPICS = ['低糖水果推荐', '富含膳食纤维的食物', '减脂期间的饮食建议', '儿童营养搭配', '食物热量查询']

interface ChatEntry {
  id: number
  role: 'user' | 'assistant' | 'error'
  content: string
  mode?: string
  citations?: Citation[]
  retryPrompt?: string
  retryHistory?: ChatMessage[]
}

const messages = ref<ChatEntry[]>([])
const draft = ref('')
const sending = ref(false)
const messagesLoading = ref(false)
const loadingOlder = ref(false)
const scrollEl = ref<HTMLElement | null>(null)
const stickToBottom = ref(true)
let nextId = 1

const conversationId = ref<number | null>(null)
const conversations = ref<ConversationSummary[]>([])
const conversationsLoading = ref(false)
const conversationsError = ref('')
const historyOpen = ref(false)
const messageTotal = ref(0)
const loadedPage = ref(1)

const isEmpty = computed(() => messages.value.length === 0)
const canSend = computed(
  () => !sending.value && draft.value.trim().length > 0 && draft.value.length <= MAX_MESSAGE_LENGTH,
)

// 删除会话做成两段式确认，避免误点把整段历史删掉
const pendingDeleteId = ref<number | null>(null)
let deleteTimer: ReturnType<typeof setTimeout> | undefined

onMounted(async () => {
  await loadConversations(true)
})

onBeforeUnmount(() => {
  if (deleteTimer) clearTimeout(deleteTimer)
})

function onScroll() {
  const el = scrollEl.value
  if (!el) return
  stickToBottom.value = el.scrollHeight - el.scrollTop - el.clientHeight < 80
}

async function scrollToBottom(force = false) {
  await nextTick()
  const el = scrollEl.value
  if (!el) return
  if (!force && !stickToBottom.value) return
  el.scrollTop = el.scrollHeight
}

function toHistory(entries: ChatEntry[]): ChatMessage[] {
  const history: ChatMessage[] = []
  for (const entry of entries) {
    if (entry.role === 'user' || entry.role === 'assistant') {
      history.push({ role: entry.role, content: entry.content })
    }
  }
  return history
}

function toEntry(message: MessageRecord): ChatEntry {
  return {
    id: nextId++,
    role: message.role === 'user' ? 'user' : 'assistant',
    content: message.content,
    mode: message.mode ?? undefined,
    citations: message.citations ?? [],
  }
}

function readStoredConversation(): number | null {
  try {
    const raw = localStorage.getItem(CURRENT_CONVERSATION_KEY)
    if (!raw) return null
    const value = Number(raw)
    return Number.isFinite(value) && value > 0 ? value : null
  } catch {
    return null
  }
}

function persistConversation(id: number | null) {
  try {
    if (id === null) localStorage.removeItem(CURRENT_CONVERSATION_KEY)
    else localStorage.setItem(CURRENT_CONVERSATION_KEY, String(id))
  } catch {
    // 隐私模式下 localStorage 可能不可用，不影响当前页面使用
  }
}

async function loadConversations(restoreCurrent = false) {
  conversationsLoading.value = true
  conversationsError.value = ''
  try {
    const data = await listConversations(1, 50)
    conversations.value = data.items

    if (restoreCurrent && conversationId.value === null) {
      const stored = readStoredConversation()
      if (stored !== null && data.items.some((item) => item.id === stored)) {
        await openConversation(stored)
      }
    }
  } catch (err) {
    conversationsError.value = err instanceof Error ? err.message : '历史会话加载失败'
  } finally {
    conversationsLoading.value = false
  }
}

async function openConversation(id: number) {
  if (sending.value || messagesLoading.value) return

  conversationId.value = id
  persistConversation(id)
  historyOpen.value = false
  messages.value = []
  messageTotal.value = 0
  loadedPage.value = 1
  messagesLoading.value = true

  try {
    const data = await listMessages(id, 1, 50)
    messages.value = data.items.map(toEntry)
    messageTotal.value = data.total
    stickToBottom.value = true
    await scrollToBottom(true)
  } catch (err) {
    messages.value = [
      {
        id: nextId++,
        role: 'error',
        content: err instanceof Error ? err.message : '历史消息加载失败',
      },
    ]
  } finally {
    messagesLoading.value = false
  }
}

async function loadOlder() {
  if (!conversationId.value || loadingOlder.value || sending.value) return
  loadingOlder.value = true
  try {
    const nextPage = loadedPage.value + 1
    const data = await listMessages(conversationId.value, nextPage, 50)
    const older = data.items.map(toEntry)
    messages.value = [...older, ...messages.value]
    loadedPage.value = nextPage
    messageTotal.value = data.total
  } catch (err) {
    messages.value.unshift({
      id: nextId++,
      role: 'error',
      content: err instanceof Error ? err.message : '更早的消息加载失败',
    })
  } finally {
    loadingOlder.value = false
  }
}

async function newConversation() {
  if (sending.value) return
  try {
    const conversation = await createConversation()
    conversations.value = [conversation, ...conversations.value]
    conversationId.value = conversation.id
    persistConversation(conversation.id)
    resetMessages()
    historyOpen.value = false
  } catch {
    // 建会话失败不阻塞本地提问：第一条消息仍可由 /chat 自动建会话
    conversationId.value = null
    persistConversation(null)
    resetMessages()
    historyOpen.value = false
  }
}

function resetMessages() {
  messages.value = []
  draft.value = ''
  messageTotal.value = 0
  loadedPage.value = 1
  stickToBottom.value = true
  pendingDeleteId.value = null
}

function toggleHistory() {
  historyOpen.value = !historyOpen.value
  if (historyOpen.value) void loadConversations(false)
}

function toggleDelete(id: number) {
  if (sending.value) return
  if (pendingDeleteId.value !== id) {
    pendingDeleteId.value = id
    if (deleteTimer) clearTimeout(deleteTimer)
    deleteTimer = setTimeout(() => {
      pendingDeleteId.value = null
    }, 3000)
    return
  }
  void removeConversation(id)
}

async function removeConversation(id: number) {
  if (deleteTimer) clearTimeout(deleteTimer)
  pendingDeleteId.value = null

  try {
    await deleteConversation(id)
    conversations.value = conversations.value.filter((item) => item.id !== id)
    if (conversationId.value === id) {
      conversationId.value = null
      persistConversation(null)
      resetMessages()
    }
  } catch (err) {
    messages.value.push({
      id: nextId++,
      role: 'error',
      content: err instanceof Error ? err.message : '删除会话失败',
    })
  }
}

function deleteCurrent() {
  if (conversationId.value !== null) {
    toggleDelete(conversationId.value)
    return
  }
  resetMessages()
}

async function requestReply(prompt: string, history: ChatMessage[]) {
  sending.value = true
  stickToBottom.value = true
  await scrollToBottom(true)

  const before = conversationId.value
  try {
    const data = await sendChatMessage(prompt, history, before ?? undefined)
    if (data.conversationId) {
      conversationId.value = data.conversationId
      persistConversation(data.conversationId)
    }
    messages.value.push({
      id: nextId++,
      role: 'assistant',
      content: data.reply,
      mode: data.mode,
      citations: data.citations ?? [],
    })
    if (before === null) {
      // 首条消息由后端自动建会话，刷新列表拿到真实标题
      await loadConversations(false)
    }
  } catch (err) {
    messages.value.push({
      id: nextId++,
      role: 'error',
      content: err instanceof Error ? err.message : '发送失败，请稍后重试',
      retryPrompt: prompt,
      retryHistory: history,
    })
  } finally {
    sending.value = false
    await scrollToBottom()
  }
}

function submit(rawText?: string) {
  if (sending.value) return

  const text = (rawText ?? draft.value).trim()
  if (!text || text.length > MAX_MESSAGE_LENGTH) return

  const history = toHistory(messages.value)
  messages.value.push({ id: nextId++, role: 'user', content: text })
  draft.value = ''
  stickToBottom.value = true
  void requestReply(text, history)
}

function retry(entry: ChatEntry) {
  if (sending.value || !entry.retryPrompt) return
  messages.value = messages.value.filter((item) => item.id !== entry.id)
  void requestReply(entry.retryPrompt, entry.retryHistory ?? [])
}

function formatTime(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function onKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter' || event.shiftKey) return
  if (event.isComposing || event.keyCode === 229) return

  event.preventDefault()
  submit()
}
</script>

<template>
  <div class="assistant-page">
    <!-- 左栏：标题、推荐问题、热门话题与品牌介绍 -->
    <div class="assistant-main">
      <header class="assistant-hero">
        <span class="assistant-hero__icon" aria-hidden="true">
          <Bot />
        </span>
        <div class="assistant-hero__text">
          <h1>AI 营养助手</h1>
          <p>了解食物成分、比较营养差异，获取有数据依据的营养知识解释。</p>
        </div>
      </header>

      <section class="assistant-welcome" aria-labelledby="assistant-welcome-title">
        <svg class="assistant-welcome__leaf" viewBox="0 0 160 110" aria-hidden="true">
          <path d="M150 6C110 0 72 16 56 52c34 4 72-14 94-46Z" fill="#DDF2E7" />
          <path d="M158 26C122 30 96 50 84 82c30-6 60-28 74-56Z" fill="#EBF8F1" />
          <path d="M130 14C104 32 86 56 78 84" stroke="#C9E9D9" stroke-width="1.8" fill="none" />
        </svg>

        <h2 id="assistant-welcome-title" class="assistant-welcome__title">
          <Sparkles aria-hidden="true" />
          今天想了解什么？
        </h2>
        <p class="assistant-welcome__desc">选择一个问题开始探索食物营养。</p>

        <div class="assistant-quick-grid">
          <button
            v-for="card in QUICK_CARDS"
            :key="card.title"
            type="button"
            class="assistant-quick"
            :disabled="sending"
            @click="submit(card.prompt)"
          >
            <span class="assistant-quick__icon" :class="`is-${card.tone}`" aria-hidden="true">
              <component :is="card.icon" />
            </span>
            <span class="assistant-quick__body">
              <strong>{{ card.title }}</strong>
              <span>{{ card.prompt }}</span>
            </span>
            <ChevronRight class="assistant-quick__arrow" aria-hidden="true" />
          </button>
        </div>
      </section>

      <section class="assistant-topics" aria-labelledby="assistant-topics-title">
        <h2 id="assistant-topics-title" class="assistant-topics__title">
          <Flame aria-hidden="true" />
          热门话题
        </h2>
        <div class="assistant-topics__list">
          <button
            v-for="topic in HOT_TOPICS"
            :key="topic"
            type="button"
            class="assistant-topic"
            :disabled="sending"
            @click="submit(topic)"
          >
            {{ topic }}
          </button>
        </div>
      </section>

      <section class="assistant-intro">
        <div class="assistant-intro__art" aria-hidden="true">
          <svg viewBox="0 0 160 130" fill="none">
            <circle cx="80" cy="66" r="58" fill="#EAF7F0" />
            <path
              d="M46 82c0-6 5-11 11-11 1-8 8-14 16-14s15 6 16 14c6 0 11 5 11 11 0 6-5 10-11 10H57c-6 0-11-4-11-10Z"
              fill="#3FA97F"
            />
            <rect x="70" y="91" width="14" height="17" rx="5" fill="#8FCBAE" />
            <path d="M108 64l16 34-23-9 7-25Z" fill="#F08A4B" />
            <path d="M116 60c2-8 8-12 14-12-2 7-6 11-14 12Z" fill="#5FB98A" />
            <path d="M120 64c5-6 12-7 18-4-5 5-12 6-18 4Z" fill="#79C9A0" />
            <circle cx="50" cy="104" r="13" fill="#EE6B5B" />
            <path d="M50 93c2-4 5-6 8-6-1 3-3 5-8 6Z" fill="#4FA57F" />
            <ellipse cx="94" cy="103" rx="15" ry="18" fill="#7DBE6A" />
            <ellipse cx="94" cy="103" rx="10" ry="13" fill="#B7DB8E" />
            <circle cx="94" cy="106" r="5" fill="#9A6B3F" />
            <path d="M124 26c8-6 17-5 22 1-8 5-16 5-22-1Z" fill="#CDEBDC" />
            <path d="M16 40c7-5 15-4 19 2-7 4-14 4-19-2Z" fill="#CDEBDC" />
          </svg>
        </div>

        <div class="assistant-intro__text">
          <h2>你好！我是你的 AI 营养助手</h2>
          <p>
            我可以基于权威的营养数据，为你提供专业、准确的营养知识解释。你可以直接提问，或从推荐问题开始。
          </p>
          <ul class="assistant-badges">
            <li><ShieldCheck aria-hidden="true" />基于权威数据</li>
            <li><Leaf aria-hidden="true" />专业营养知识</li>
            <li><MessagesSquare aria-hidden="true" />支持多轮对话</li>
          </ul>
        </div>
      </section>
    </div>

    <!-- 右栏：聊天面板 -->
    <section class="assistant-chat" aria-label="对话记录">
      <header class="assistant-chat__head">
        <MessageSquareText class="assistant-chat__icon" aria-hidden="true" />
        <h2>对话记录</h2>
        <div class="assistant-chat__tools">
          <button
            type="button"
            class="assistant-chat__action"
            title="历史会话"
            aria-label="历史会话"
            :aria-expanded="historyOpen"
            @click="toggleHistory"
          >
            <History aria-hidden="true" />
          </button>
          <button
            type="button"
            class="assistant-chat__action"
            title="新建会话"
            aria-label="新建会话"
            :disabled="sending"
            @click="newConversation"
          >
            <Plus aria-hidden="true" />
          </button>
          <button
            type="button"
            class="assistant-chat__action"
            :title="conversationId !== null && pendingDeleteId === conversationId ? '再次点击确认删除' : '删除当前会话'"
            aria-label="删除当前会话"
            :disabled="sending || (conversationId === null && isEmpty)"
            @click="deleteCurrent"
          >
            <Trash2 aria-hidden="true" />
          </button>
        </div>
      </header>

      <div v-if="historyOpen" class="assistant-history__backdrop" @click="historyOpen = false"></div>
      <aside v-if="historyOpen" class="assistant-history" aria-label="历史会话列表">
        <div class="assistant-history__head">
          <strong>历史会话</strong>
          <button type="button" class="assistant-history__new" :disabled="sending" @click="newConversation">
            <Plus aria-hidden="true" />
            新对话
          </button>
          <button type="button" class="assistant-history__close" aria-label="关闭" @click="historyOpen = false">
            <X aria-hidden="true" />
          </button>
        </div>

        <div v-if="conversationsLoading" class="assistant-history__state">
          <LoaderCircle class="is-spinning" aria-hidden="true" />
          加载中
        </div>
        <div v-else-if="conversationsError" class="assistant-history__state is-error">
          <span>{{ conversationsError }}</span>
          <button type="button" @click="loadConversations(false)">重试</button>
        </div>
        <p v-else-if="conversations.length === 0" class="assistant-history__state">还没有历史会话</p>
        <ul v-else class="assistant-history__list">
          <li
            v-for="conversation in conversations"
            :key="conversation.id"
            :class="{ 'is-active': conversation.id === conversationId }"
          >
            <button
              type="button"
              class="assistant-history__item"
              :disabled="sending"
              @click="openConversation(conversation.id)"
            >
              <span class="assistant-history__title">{{ conversation.title }}</span>
              <span class="assistant-history__time">{{ formatTime(conversation.updatedAt) }}</span>
            </button>
            <button
              type="button"
              class="assistant-history__delete"
              :class="{ 'is-confirming': pendingDeleteId === conversation.id }"
              :title="pendingDeleteId === conversation.id ? '再次点击确认删除' : '删除会话'"
              :disabled="sending"
              @click.stop="toggleDelete(conversation.id)"
            >
              <Trash2 aria-hidden="true" />
            </button>
          </li>
        </ul>
      </aside>

      <div
        ref="scrollEl"
        class="assistant-messages"
        role="log"
        aria-live="polite"
        @scroll="onScroll"
      >
        <div v-if="messagesLoading" class="assistant-loading">
          <LoaderCircle class="is-spinning" aria-hidden="true" />
          正在加载历史消息
        </div>

        <div v-else-if="isEmpty" class="assistant-empty">
          <span class="assistant-empty__icon" aria-hidden="true">
            <MessageCircle />
            <svg class="assistant-empty__leaf" viewBox="0 0 18 18" fill="none">
              <path d="M17 1C9 1.7 4 5.5 2.2 12 8.4 11.3 14 7.4 17 1Z" fill="currentColor" />
            </svg>
          </span>
          <h3>还没有对话记录</h3>
          <p>你可以从左侧的推荐问题开始，或者直接输入你想了解的问题。</p>
          <p class="assistant-empty__demo">回答基于食物营养库与知识库，仅供知识参考</p>
        </div>

        <template v-else>
          <button
            v-if="messageTotal > messages.length"
            type="button"
            class="assistant-load-older"
            :disabled="loadingOlder"
            @click="loadOlder"
          >
            <LoaderCircle v-if="loadingOlder" class="is-spinning" aria-hidden="true" />
            {{ loadingOlder ? '加载中' : '加载更早消息' }}
          </button>

          <div
            v-for="entry in messages"
            :key="entry.id"
            class="assistant-row"
            :class="`is-${entry.role}`"
          >
            <span v-if="entry.role === 'assistant'" class="assistant-avatar" aria-hidden="true">
              <Bot />
            </span>

            <div
              class="assistant-bubble"
              :class="{
                'assistant-bubble--user': entry.role === 'user',
                'assistant-bubble--assistant': entry.role === 'assistant',
                'assistant-bubble--error': entry.role === 'error',
              }"
            >
              <span
                v-if="entry.role === 'assistant' && entry.mode === 'placeholder'"
                class="assistant-mode"
              >
                演示模式 · AI 服务未接入
              </span>
              <span
                v-else-if="entry.role === 'assistant' && entry.mode === 'rag' && entry.citations?.length"
                class="assistant-mode is-rag"
              >
                知识库引用
              </span>

              <span v-if="entry.role === 'error'" class="assistant-error__title">
                <CircleAlert aria-hidden="true" />
                发送失败
              </span>

              <p class="assistant-text">{{ entry.content }}</p>

              <div
                v-if="entry.role === 'assistant' && entry.citations && entry.citations.length"
                class="assistant-citations"
              >
                <details
                  v-for="citation in entry.citations"
                  :key="citation.documentId"
                  class="assistant-citation"
                >
                  <summary>
                    <BookOpen aria-hidden="true" />
                    <span class="assistant-citation__title">{{ citation.title }}</span>
                    <span class="assistant-citation__source">{{ citation.source }}</span>
                  </summary>
                  <p class="assistant-citation__snippet">{{ citation.snippet }}</p>
                  <a
                    v-if="citation.url"
                    class="assistant-citation__link"
                    :href="citation.url"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <ExternalLink aria-hidden="true" />
                    查看来源
                  </a>
                </details>
              </div>

              <button
                v-if="entry.role === 'error' && entry.retryPrompt"
                type="button"
                class="assistant-retry"
                :disabled="sending"
                @click="retry(entry)"
              >
                <RotateCcw aria-hidden="true" />
                <span>重试</span>
              </button>
            </div>
          </div>
        </template>

        <div v-if="sending" class="assistant-row is-assistant">
          <span class="assistant-avatar" aria-hidden="true">
            <Bot />
          </span>
          <div
            class="assistant-bubble assistant-bubble--assistant assistant-typing"
            aria-label="正在思考"
          >
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>

      <form class="assistant-composer" @submit.prevent="submit()">
        <div class="assistant-input-box">
          <label class="assistant-sr-only" for="assistant-input">输入你的营养问题</label>
          <textarea
            id="assistant-input"
            v-model="draft"
            class="assistant-input"
            rows="2"
            :maxlength="MAX_MESSAGE_LENGTH"
            :disabled="sending"
            placeholder="输入你想了解的问题……"
            @keydown="onKeydown"
          ></textarea>
          <div class="assistant-composer__foot">
            <span class="assistant-shortcut">Enter 发送 · Shift + Enter 换行</span>
            <div class="assistant-composer__right">
              <span class="assistant-counter">{{ draft.length }}/{{ MAX_MESSAGE_LENGTH }}</span>
              <button type="submit" class="assistant-send" :disabled="!canSend">
                <Send aria-hidden="true" />
                <span>{{ sending ? '发送中' : '发送' }}</span>
              </button>
            </div>
          </div>
        </div>
      </form>
    </section>
  </div>
</template>