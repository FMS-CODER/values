package ming.valuesjava.dto;

import java.math.BigDecimal;

/**
 * 详情页营养格。nrvPercent 为 null 表示该营养素没有规定 NRV，前端据此隐藏百分比。
 */
public record NutrientTileDto(
        String code,
        String name,
        String unit,
        BigDecimal amount,
        BigDecimal nrvPercent) {
}