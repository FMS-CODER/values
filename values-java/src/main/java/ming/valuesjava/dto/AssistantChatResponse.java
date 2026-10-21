package ming.valuesjava.dto;

import java.util.List;

/**
 * AI 助手对话响应。
 *
 * mode 用于区分「真实模型回答」与「占位回答」：
 * 前端据此在界面上标注状态，避免把固定文案误当成 AI 给出的营养结论。
 * suggestions 只在占位模式下返回，作为引导用户操作的快捷问题。
 */
public record AssistantChatResponse(String reply, String mode, List<String> suggestions) {
}