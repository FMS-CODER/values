package ming.valuesjava.dto;

/**
 * 图片审核状态变更请求体。
 * 做成对象而不是裸字符串，是为了给前端一个明确的字段名 status，也便于以后扩展备注字段。
 */
public record ImageReviewRequest(String status) {
}