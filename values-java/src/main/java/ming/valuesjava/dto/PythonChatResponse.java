package ming.valuesjava.dto;

import java.util.List;

/** Python AI 服务的原始响应；与 AssistantChatResponse 分开，避免把 Java 侧 ID 序列化给 Python。 */
public record PythonChatResponse(
        String reply,
        String mode,
        List<String> suggestions,
        List<CitationDto> citations,
        String intent) {
}