package ming.valuesjava.dto;

import java.util.List;

/**
 * AI 助手对话请求。
 *
 * conversationId 为空时保持旧版行为：后端自动创建会话并落库，响应会带回新 ID；
 * history 仍保留给旧客户端，服务端有 conversationId 时以数据库中的历史为准。
 */
public record AssistantChatRequest(
        String message,
        List<AssistantMessage> history,
        Long conversationId) {

    /** 单条消息；role 只允许 user / assistant */
    public record AssistantMessage(String role, String content) {
    }
}