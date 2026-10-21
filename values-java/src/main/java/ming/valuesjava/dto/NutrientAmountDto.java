package ming.valuesjava.dto;

import java.math.BigDecimal;

/**
 * 列表卡片上的单项营养值（只包含 show_in_card = 1 的四项）。
 * amount 用 BigDecimal，避免 DECIMAL 数值在 JSON 序列化时出现浮点误差。
 */
public record NutrientAmountDto(
        String code,
        String name,
        String unit,
        BigDecimal amount) {
}