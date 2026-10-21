package ming.valuesjava.dto;

/**
 * 食物新增/修改请求体。
 * sourceId 不在前端表单里，但保留可选注入：不传时由服务端回落到 USDA_FOUNDATION，
 * 这样普通录入不必关心来源字典，导入类操作仍能指定真实来源。
 * verified 用包装类型是为了区分「未传」（按 false 处理）与显式 true。
 */
public record FoodRequest(
        String name,
        String nameEn,
        Long categoryId,
        String imageUrl,
        String description,
        String state,
        Long fdcId,
        Boolean verified,
        String sourceNote,
        String claimNote,
        Integer sourceId) {
}