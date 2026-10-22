package ming.valuesjava.dto;

/** 新建会话；title 为空时由后端生成「新对话」。 */
public record ConversationCreateRequest(String title) {
}