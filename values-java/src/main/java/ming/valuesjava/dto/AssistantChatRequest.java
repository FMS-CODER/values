package ming.valuesjava.dto;

import java.util.List;

/**
 * AI 助手对话请求。
 *
 * history 由前端回传最近若干轮上下文，而不是让服务端存会话：
 * 当前没有登录体系，服务端无法识别「谁」的会话，放在客户端更简单；
 * 真正接入 LangGraph 后如果要做多轮记忆，再换成服务端会话 ID。
 */
public record AssistantChatRequest(String message, List<AssistantMessage> history) {

    /** 单条消息；role 只允许 user / assistant */
    public record AssistantMessage(String role, String content) {
    }
}