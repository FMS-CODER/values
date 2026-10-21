package ming.valuesjava.dto;

import java.util.List;

/**
 * 食物详情。
 * nutrientTiles 为全部营养素（按 sort_order），highlights 只保留达到「富含」条件且有科普说明的项。
 */
public record FoodDetailDto(
        Long id,
        String name,
        String categoryCode,
        String categoryName,
        String imageUrl,
        String description,
        String state,
        String claimNote,
        SourceDto source,
        RuleStandardDto ruleStandard,
        List<NutrientTileDto> nutrientTiles,
        List<HighlightDto> highlights) {
}