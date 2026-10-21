package ming.valuesjava.dto;

/**
 * 统一错误响应。
 * 前端按 HTTP 状态码分支，body 只保证 message 一个字段可读，
 * 因此不把异常栈、SQL 语句等内部信息放进这里。
 */
public record ApiErrorResponse(String message) {
}