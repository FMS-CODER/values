package ming.valuesjava.dto;

/**
 * 管理端食物完整对象，供编辑表单回填。
 * 同时给出 categoryId（提交时使用）与 categoryCode/categoryName（展示时使用），
 * 前端不必为了显示名称再查一次分类字典。
 */
public record AdminFoodDetailDto(
        Long id,
        String name,
        String nameEn,
        Long categoryId,
        String categoryCode,
        String categoryName,
        String imageUrl,
        String description,
        String state,
        Long fdcId,
        String ndbNumber,
        String dataType,
        String publicationDate,
        Integer sourceId,
        String sourceName,
        String sourceRecordId,
        boolean verified,
        String sourceNote,
        String claimNote) {
}