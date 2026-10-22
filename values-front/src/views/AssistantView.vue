<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import {
  Apple,
  Bot,
  ChevronRight,
  CircleAlert,
  EllipsisVertical,
  Flame,
  Leaf,
  MessageCircle,
  MessageSquareText,
  MessagesSquare,
  RotateCcw,
  Salad,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  Trash2,
  UtensilsCrossed,
} from 'lucide-vue-next'
import { sendChatMessage } from '@/services/assistant'
import type { ChatMessage } from '@/types/assistant'

const MAX_MESSAGE_LENGTH = 1000

/**
 * 推荐问题卡片。文案与后端 placeholder 返回的 suggestions 同源，
 * 点击后走与输入框完全相同的 submit()，不另建一套发送逻辑。
 */
const QUICK_CARDS = [
  { title: '食物营养分析', prompt: '西兰花有哪些营养亮点？', icon: Salad, tone: 'green' },
  { title: '营养成分对比', prompt: '鸡胸肉和牛里脊的营养有什么区别？', icon: UtensilsCrossed, tone: 'coral' },
  { title: '了解营养素', prompt: '维生素 C 含量高的食物有哪些？', icon: Apple, tone: 'orange' },
  { title: '寻找高蛋白食物', prompt: '哪些食物的蛋白质含量较高？', icon: Search, tone: 'blue' },
]

/** 热门话题只是把用户常问的问题做成快捷入口，不代表服务已支持这些专项能力 */
const HOT_TOPICS = ['低糖水果推荐', '富含膳食纤维的食物', '减脂期间的饮食建议', '儿童营养搭配', '食物热量查询']

/**
 * 页面内的对话条目。错误也单独成条：
 * 它既不是用户提问也不是助手回答，混进任意一边都会让人误以为模型给出了结论。
 */
interface ChatEntry {
  id: number
  role: 'user' | 'assistant' | 'error'
  content: string
  /** 助手回复的模式，'placeholder' 表示后端仍是占位实现 */
  mode?: string
  /** 失败时保存原始问题，供「重试」重发 */
  retryPrompt?: string
  /** 失败时保存当时的上下文，重试时不会把失败的那条问题重复塞进历史 */
  retryHistory?: ChatMessage[]
}

const messages = ref<ChatEntry[]>([])
const draft = ref('')
const sending = ref(false)
const scrollEl = ref<HTMLElement | null>(null)
/** 用户手动上滑查看历史时置为 false，避免新消息把视图强行拉回底部 */
const stickToBottom = ref(true)
let nextId = 1

const isEmpty = computed(() => messages.value.length === 0)
const canSend = computed(
  () => !sending.value && draft.value.trim().length > 0 && draft.value.length <= MAX_MESSAGE_LENGTH,
)

// 清空是一次性动作，做成两段式确认（而不是弹窗），避免误点丢失当前对话
const confirmClear = ref(false)
let confirmTimer: ReturnType<typeof setTimeout> | undefined

// 聊天头部的三点菜单。只有「清空对话」一个真实入口，不做多会话的假菜单
const menuOpen = ref(false)

function toggleMenu() {
  menuOpen.value = !menuOpen.value
}

function closeMenu() {
  menuOpen.value = false
}

function clearFromMenu() {
  if (isEmpty.value || sending.value) return

  // 与左侧按钮共用同一套两段式确认，避免两个入口行为不一致
  const willClear = confirmClear.value
  onClearClick()
  if (willClear) closeMenu()
}

onBeforeUnmount(() => {
  if (confirmTimer) clearTimeout(confirmTimer)
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

/**
 * 只回传真正的对话内容。错误条目如果进了 history，
 * 后端会把它当成上下文的一部分，后续回复会围绕报错展开。
 */
function toHistory(entries: ChatEntry[]): ChatMessage[] {
  const history: ChatMessage[] = []
  for (const entry of entries) {
    if (entry.role === 'user' || entry.role === 'assistant') {
      history.push({ role: entry.role, content: entry.content })
    }
  }
  return history
}

async function requestReply(prompt: string, history: ChatMessage[]) {
  sending.value = true
  await scrollToBottom(true)

  try {
    const data = await sendChatMessage(prompt, history)
    messages.value.push({
      id: nextId++,
      role: 'assistant',
      content: data.reply,
      mode: data.mode,
    })
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
  // 用户主动发送时强制回到底部，否则回复会出现在看不见的位置
  stickToBottom.value = true
  void requestReply(text, history)
}

function retry(entry: ChatEntry) {
  if (sending.value || !entry.retryPrompt) return

  // 重试成功后不该再留着上一条报错，否则用户会以为仍然失败
  messages.value = messages.value.filter((item) => item.id !== entry.id)
  void requestReply(entry.retryPrompt, entry.retryHistory ?? [])
}

function clearChat() {
  if (sending.value) return
  messages.value = []
  draft.value = ''
  stickToBottom.value = true
}

function onClearClick() {
  if (isEmpty.value || sending.value) return

  if (!confirmClear.value) {
    confirmClear.value = true
    if (confirmTimer) clearTimeout(confirmTimer)
    confirmTimer = setTimeout(() => {
      confirmClear.value = false
    }, 3000)
    return
  }

  if (confirmTimer) clearTimeout(confirmTimer)
  confirmClear.value = false
  clearChat()
}

function onKeydown(event: KeyboardEvent) {
  if (event.key !== 'Enter' || event.shiftKey) return
  // 中文/日文输入法用 Enter 确认候选词，此时不能当作发送
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
        <button
          type="button"
          class="assistant-clear"
          :class="{ 'is-confirming': confirmClear }"
          :disabled="isEmpty || sending"
          @click="onClearClick"
        >
          <Trash2 aria-hidden="true" />
          <span>{{ confirmClear ? '确认清空？' : '清空对话' }}</span>
        </button>
      </header>

      <section class="assistant-welcome" aria-labelledby="assistant-welcome-title">
        <!-- 右上角叶片只是装饰，用内联 SVG 画，免得为一块装饰再引入图片资源 -->
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
        <!-- 用内联 SVG 画一组蔬果，替代照片拼贴：矢量不糊、不新增图片文件，也更接近原型的插画感 -->
        <div class="assistant-intro__art" aria-hidden="true">
          <svg viewBox="0 0 160 130" fill="none">
            <circle cx="80" cy="66" r="58" fill="#EAF7F0" />

            <!-- 西兰花 -->
            <path
              d="M46 82c0-6 5-11 11-11 1-8 8-14 16-14s15 6 16 14c6 0 11 5 11 11 0 6-5 10-11 10H57c-6 0-11-4-11-10Z"
              fill="#3FA97F"
            />
            <rect x="70" y="91" width="14" height="17" rx="5" fill="#8FCBAE" />

            <!-- 胡萝卜 -->
            <path d="M108 64l16 34-23-9 7-25Z" fill="#F08A4B" />
            <path d="M116 60c2-8 8-12 14-12-2 7-6 11-14 12Z" fill="#5FB98A" />
            <path d="M120 64c5-6 12-7 18-4-5 5-12 6-18 4Z" fill="#79C9A0" />

            <!-- 番茄 -->
            <circle cx="50" cy="104" r="13" fill="#EE6B5B" />
            <path d="M50 93c2-4 5-6 8-6-1 3-3 5-8 6Z" fill="#4FA57F" />

            <!-- 牛油果 -->
            <ellipse cx="94" cy="103" rx="15" ry="18" fill="#7DBE6A" />
            <ellipse cx="94" cy="103" rx="10" ry="13" fill="#B7DB8E" />
            <circle cx="94" cy="106" r="5" fill="#9A6B3F" />

            <!-- 点缀叶片 -->
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
        <div class="assistant-chat__menu">
          <button
            type="button"
            class="assistant-chat__action"
            title="更多操作"
            aria-label="更多操作"
            :aria-expanded="menuOpen"
            @click="toggleMenu"
          >
            <EllipsisVertical aria-hidden="true" />
          </button>

          <!-- 只有一个真实入口，不伪装成多会话管理 -->
          <div v-if="menuOpen" class="assistant-menu__backdrop" @click="closeMenu"></div>
          <div v-if="menuOpen" class="assistant-menu">
            <button
              type="button"
              class="assistant-menu__item"
              :disabled="isEmpty || sending"
              @click="clearFromMenu"
            >
              <Trash2 aria-hidden="true" />
              <span>{{ confirmClear ? '确认清空？' : '清空对话' }}</span>
            </button>
          </div>
        </div>
      </header>

      <div
        ref="scrollEl"
        class="assistant-messages"
        role="log"
        aria-live="polite"
        @scroll="onScroll"
      >
        <div v-if="isEmpty" class="assistant-empty">
          <span class="assistant-empty__icon" aria-hidden="true">
            <MessageCircle />
            <svg class="assistant-empty__leaf" viewBox="0 0 18 18" fill="none">
              <path d="M17 1C9 1.7 4 5.5 2.2 12 8.4 11.3 14 7.4 17 1Z" fill="currentColor" />
            </svg>
          </span>
          <h3>还没有对话记录</h3>
          <p>你可以从左侧的推荐问题开始，或者直接输入你想了解的问题。</p>
          <!-- 说明回答依据，避免把模型输出误当成临床或膳食建议 -->
          <p class="assistant-empty__demo">回答基于食物营养库数据，仅供知识参考</p>
        </div>

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

            <span v-if="entry.role === 'error'" class="assistant-error__title">
              <CircleAlert aria-hidden="true" />
              发送失败
            </span>

            <p class="assistant-text">{{ entry.content }}</p>

            <button
              v-if="entry.role === 'error'"
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