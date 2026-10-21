<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { Bot, CircleAlert, RotateCcw, Send, Sparkles, Trash2 } from 'lucide-vue-next'
import { sendChatMessage } from '@/services/assistant'
import type { ChatMessage } from '@/types/assistant'

const MAX_MESSAGE_LENGTH = 1000

/** 空状态的推荐问题，和后端 placeholder 返回的 suggestions 保持一致 */
const SUGGESTIONS = ['西兰花有哪些营养亮点？', '高蛋白的食物有哪些？', '苹果的维生素 C 算高吗？']

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
let nextId = 1

const isEmpty = computed(() => messages.value.length === 0)
const canSend = computed(
  () => !sending.value && draft.value.trim().length > 0 && draft.value.length <= MAX_MESSAGE_LENGTH,
)

async function scrollToBottom() {
  await nextTick()
  const el = scrollEl.value
  if (!el) return
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
  await scrollToBottom()

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
    <header class="assistant-head">
      <div class="assistant-head__text">
        <div class="assistant-head__title">
          <h1>AI 营养助手</h1>
          <span class="assistant-proto">原型</span>
        </div>
        <p class="assistant-head__note">
          这是原型页面，后台 AI 服务（LangGraph）尚未接入：当前回复只是后端返回的占位说明，用来验证对话链路，不能作为营养或医学建议。
        </p>
      </div>
      <button
        type="button"
        class="assistant-clear"
        :disabled="isEmpty || sending"
        @click="clearChat"
      >
        <Trash2 aria-hidden="true" />
        <span>清空对话</span>
      </button>
    </header>

    <section class="assistant-panel" aria-label="AI 营养助手对话">
      <div ref="scrollEl" class="assistant-messages" role="log" aria-live="polite">
        <div v-if="isEmpty" class="assistant-welcome">
          <span class="assistant-welcome__icon">
            <Bot aria-hidden="true" />
          </span>
          <h2 class="assistant-welcome__title">从一句话开始了解食物营养</h2>
          <p class="assistant-welcome__text">
            助手服务还在建设中，现在发送消息会拿到后端的占位说明。你可以先用下面的问题走一遍完整流程。
          </p>
          <p class="assistant-welcome__label">可以试试</p>
          <div class="assistant-suggestions">
            <button
              v-for="item in SUGGESTIONS"
              :key="item"
              type="button"
              class="assistant-suggestion"
              :disabled="sending"
              @click="submit(item)"
            >
              <Sparkles aria-hidden="true" />
              <span>{{ item }}</span>
            </button>
          </div>
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
          <div class="assistant-bubble assistant-bubble--assistant assistant-typing" aria-label="正在思考">
            <span></span>
            <span></span>
            <span></span>
          </div>
        </div>
      </div>

      <form class="assistant-composer" @submit.prevent="submit()">
        <label class="assistant-sr-only" for="assistant-input">输入你的营养问题</label>
        <textarea
          id="assistant-input"
          v-model="draft"
          class="assistant-input"
          rows="2"
          :maxlength="MAX_MESSAGE_LENGTH"
          :disabled="sending"
          placeholder="例如：西兰花有哪些营养亮点？（Enter 发送，Shift + Enter 换行）"
          @keydown="onKeydown"
        ></textarea>
        <div class="assistant-composer__foot">
          <span class="assistant-counter">{{ draft.length }}/{{ MAX_MESSAGE_LENGTH }}</span>
          <button type="submit" class="assistant-send" :disabled="!canSend">
            <Send aria-hidden="true" />
            <span>{{ sending ? '发送中' : '发送' }}</span>
          </button>
        </div>
      </form>
    </section>
  </div>
</template>