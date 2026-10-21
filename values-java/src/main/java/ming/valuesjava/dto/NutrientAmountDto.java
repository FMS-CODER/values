package ming.valuesjava.dto;

import java.math.BigDecimal;

/**
 * 列表卡片上的单项营养值（固定为 show_in_card = 1 的四项）。
 * amount 用 BigDecimal，避免 DECIMAL 数值在 JSON 序列化时出现浮点误差；
 * amount 允许为 null：少数食物在 USDA 源数据里缺该项，接口仍返回完整 4 个槽位，前端据此显示「—」。
 */
public record NutrientAmountDto(
        String code,
        String name,
        String unit,
        BigDecimal amount) {
}