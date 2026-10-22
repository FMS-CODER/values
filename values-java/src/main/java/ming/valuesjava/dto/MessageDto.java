package ming.valuesjava.dto;

import java.time.LocalDateTime;
import java.util.List;

/** 持久化后的单条消息。 */
public record MessageDto(
        Long id,
        String role,
        String content,
        List<CitationDto> citations,
        String mode,
        String status,
        LocalDateTime createdAt) {
}