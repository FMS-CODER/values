package ming.valuesjava.dto;

import java.time.LocalDateTime;

/** 会话摘要，用于历史会话列表。 */
public record ConversationDto(
        Long id,
        String title,
        LocalDateTime createdAt,
        LocalDateTime updatedAt) {
}