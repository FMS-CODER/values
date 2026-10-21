package ming.valuesjava.dto;

import java.util.List;

/**
 * 食物列表项。nutrients 只带卡片需要的四项，详情页的完整数据由 FoodDetailDto 提供。
 * imageUrl、description 可为 null：新库中多数食物没有配图，前端需容忍缺省。
 */
public record FoodSummaryDto(
        Long id,
        String name,
        String categoryCode,
        String categoryName,
        String imageUrl,
        String description,
        List<NutrientAmountDto> nutrients) {
}