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
 * 发起请求并解析 JSON。
 * 非 2xx 抛出带状态码的 HttpError；网络不可达统一转成可读提示，
 * 避免把浏览器的 "Failed to fetch" 原样展示给用户。
 * 失败处留一条前端日志，只记录路径与状态码，不带业务数据。
 */
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
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
    console.error('[api] 请求失败', path, response.status)
    throw new HttpError(response.status, `请求失败（HTTP ${response.status}）`)
  }

  return (await response.json()) as T
}