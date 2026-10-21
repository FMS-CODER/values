package ming.valuesjava.dto;

/**
 * 管理端分类行。
 * 带上 foodCount 是为了让管理页在用户点删除前就能提示「该分类下还有多少食物」，
 * 而不是等提交后只收到一个 409；数据仍以数据库实时统计为准，前端不自行累加。
 */
public record AdminCategoryDto(
        Long id,
        String code,
        String name,
        int sortOrder,
        long foodCount) {
}