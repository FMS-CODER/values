package ming.valuesjava.dto;

/**
 * 数据来源信息。recordId 可能为空（演示数据没有外部记录号），前端需容忍 null。
 */
public record SourceDto(
        String name,
        String recordId,
        boolean verified,
        String note) {
}