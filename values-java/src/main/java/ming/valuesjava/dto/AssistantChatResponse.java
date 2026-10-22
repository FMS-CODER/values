package ming.valuesjava.dto;

import java.util.List;

/**
 * AI 助手对话响应。
 *
 * mode：llm=模型生成，database=营养库直答，rag=知识库引用，placeholder=服务降级。
 * citations 为真实引用；conversationId / assistantMessageId 用于前端恢复历史与失败重试。
 */
public record AssistantChatResponse(
        String reply,
        String mode,
        List<String> suggestions,
        List<CitationDto> citations,
        Long conversationId,
        Long assistantMessageId,
        String intent) {
}