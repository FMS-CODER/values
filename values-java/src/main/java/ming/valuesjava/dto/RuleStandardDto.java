package ming.valuesjava.dto;

/**
 * 营养声称判定依据的标准信息。effectiveDate 已格式化为 yyyy-MM-dd 字符串，避免前端处理时区。
 */
public record RuleStandardDto(
        String name,
        String effectiveDate) {
}