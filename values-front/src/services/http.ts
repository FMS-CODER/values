/**
 * 基于原生 fetch 的请求封装，避免引入额外依赖。
 */

/**
 * 带上 HTTP 状态码的错误。
 * 详情页需要区分「404 未找到」与其它网络/服务端错误以展示不同状态，
 * 因此把状态码显式暴露出来，供调用方判断。
 */
export class HttpError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'HttpError'
    this.status = status
  }
}

/**
 * 从错误响应里取出后端给的 message。
 * 后端统一返回 {"message":"..."}，直接把它展示给管理员比「HTTP 409」有用得多
 * （例如「该分类下仍有 3 个食物，无法删除」）。解析不出来再回退到通用文案，
 * 因为网关异常时返回的可能是 HTML 而不是 JSON。
 */
async function readErrorMessage(response: Response): Promise<string> {
  try {
    const payload: unknown = await response.json()
    if (payload && typeof payload === 'object' && 'message' in payload) {
      const message = (payload as { message?: unknown }).message
      if (typeof message === 'string' && message.trim()) return message
    }
  } catch {
    // 非 JSON 响应体，交给下面的兜底文案
  }

  return `请求失败（HTTP ${response.status}）`
}

/**
 * 发起请求并解析 JSON。
 * 非 2xx 抛出带状态码的 HttpError；网络不可达统一转成可读提示，
 * 避免把浏览器的 "Failed to fetch" 原样展示给用户。
 * 失败处留一条前端日志，只记录路径与状态码，不带业务数据。
 */
async function send<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response

  try {
    response = await fetch(path, {
      headers: { Accept: 'application/json' },
      ...init,
    })
  } catch (err) {
    // 原始错误打到控制台保留诊断信息，抛给调用方的是可直接展示的文案
    console.error('[api] 请求异常', path, err)
    throw new Error('无法连接服务，请确认后端已启动')
  }

  if (!response.ok) {
    const message = await readErrorMessage(response)
    console.error('[api] 请求失败', path, response.status)
    throw new HttpError(response.status, message)
  }

  // 204 表示成功但没有响应体，此时调用 response.json() 会抛 SyntaxError
  if (response.status === 204) return undefined as T

  return (await response.json()) as T
}

/** 只读请求（GET），保持原有调用方式不变 */
export function request<T>(path: string, init?: RequestInit): Promise<T> {
  return send<T>(path, init)
}

/**
 * 带 JSON 请求体的写请求。
 * 统一在这里序列化并补 Content-Type，避免每个 service 各写一遍容易漏掉。
 */
export function requestJson<T>(
  path: string,
  method: 'POST' | 'PUT' | 'PATCH' | 'DELETE',
  body?: unknown,
): Promise<T> {
  return send<T>(path, {
    method,
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
}