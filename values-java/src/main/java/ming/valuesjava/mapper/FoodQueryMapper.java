package ming.valuesjava.mapper;

import java.util.List;

import org.apache.ibatis.annotations.Param;

import ming.valuesjava.repository.FoodQueryRepository.CardNutrientRow;
import ming.valuesjava.repository.FoodQueryRepository.CategoryRow;
import ming.valuesjava.repository.FoodQueryRepository.FoodDetailRow;
import ming.valuesjava.repository.FoodQueryRepository.FoodSummaryRow;
import ming.valuesjava.repository.FoodQueryRepository.HighlightRow;
import ming.valuesjava.repository.FoodQueryRepository.NutrientTileRow;
import ming.valuesjava.repository.FoodQueryRepository.RuleStandardRow;

/**
 * 前台只读查询 Mapper。
 *
 * 这些 SQL 要么联表（food + food_category + data_source），要么直接查视图
 * （v_food_nutrient_nrv、v_food_highlight），用 XML 维护比在 Java 里拼字符串更清晰；
 * 返回类型仍是 FoodQueryRepository 里的行 record，数值口径与接口契约保持原样。
 */
public interface FoodQueryMapper {

    List<CategoryRow> findCategories();

    List<FoodSummaryRow> findFoodSummaries();

    /** 一次取回所有食物的卡片营养素，供 service 按 food_id 分组，避免 N+1 */
    List<CardNutrientRow> findCardNutrients();

    FoodDetailRow findFoodDetail(@Param("foodId") long foodId);

    List<NutrientTileRow> findNutrientTiles(@Param("foodId") long foodId);

    List<HighlightRow> findHighlights(@Param("foodId") long foodId);

    RuleStandardRow findRuleStandard();
}