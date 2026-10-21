package ming.valuesjava.dto;

import java.math.BigDecimal;

/**
 * 详情页营养格。
 * group 是稳定的分组代码（PROXIMATE/VITAMIN/MINERAL/FATTY_ACID），中文组名由前端映射，后端不参与拼装。
 * nrvPercent 为 null 表示该营养素没有规定 NRV，前端据此隐藏百分比。
 */
public record NutrientTileDto(
        String code,
        String name,
        String unit,
        String group,
        BigDecimal amount,
        BigDecimal nrvPercent) {
}