package ming.valuesjava.dto;

/**
 * 管理端食物列表行。
 * 只放列表需要的字段，避免把 19 列全部塞进分页响应；
 * updatedAt 统一格式化为「yyyy-MM-dd HH:mm」字符串，前端不需要再处理时区。
 */
public record AdminFoodSummaryDto(
        Long id,
        String name,
        String nameEn,
        String categoryCode,
        String categoryName,
        String imageUrl,
        String description,
        String state,
        Long fdcId,
        boolean verified,
        String updatedAt) {
}