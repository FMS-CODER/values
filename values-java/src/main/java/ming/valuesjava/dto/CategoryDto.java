package ming.valuesjava.dto;

/**
 * 食物分类字典项。
 * 用 record 承载只读响应，避免为纯查询场景引入可变实体。
 */
public record CategoryDto(
        String code,
        String name,
        int sortOrder) {
}