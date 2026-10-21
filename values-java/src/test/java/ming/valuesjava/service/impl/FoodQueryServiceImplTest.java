package ming.valuesjava.service.impl;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

import org.junit.jupiter.api.Test;

import ming.valuesjava.dto.FoodDetailDto;
import ming.valuesjava.dto.HighlightDto;
import ming.valuesjava.repository.FoodQueryRepository;
import ming.valuesjava.repository.FoodQueryRepository.FoodDetailRow;
import ming.valuesjava.repository.FoodQueryRepository.HighlightRow;
import ming.valuesjava.repository.FoodQueryRepository.NutrientTileRow;
import ming.valuesjava.repository.FoodQueryRepository.RuleStandardRow;

/**
 * 覆盖 service 里两处纯格式转换，它们最容易被 DECIMAL 的定标值坑到：
 * 1. 规则文案：「每 100g ≥30% NRV」不能输出成「≥30.00% NRV」；
 * 2. 数值归一化：34.0000 要输出成 34，且不能变成 3.4E+1 这种科学计数法。
 * 这两点直接决定页面显示是否正确，之前也确实出现过阈值带多余小数的问题，因此单独覆盖。
 */
class FoodQueryServiceImplTest {

    /** 苹果：只用到详情装配，字段值与库中演示数据一致 */
    private static final FoodDetailRow APPLE = new FoodDetailRow(
            2L, "苹果", "FRUIT", "水果", "/foods/apple.jpg", "含有膳食纤维和多种营养成分，适合作为日常水果选择。",
            "生，带皮", null, "171688", true, "USDA SR Legacy 食品记录，FDC ID 171688。", "USDA SR Legacy");

    private final FoodQueryRepository repository = mock(FoodQueryRepository.class);
    private final FoodQueryServiceImpl service = new FoodQueryServiceImpl(repository);

    @Test
    void buildRuleLabel_removesTrailingZerosOfThreshold() {
        stubDetail();
        // 蛋白质走绝对含量口径（库中阈值是 DECIMAL(12,3) = 12.000），钾走 NRV 百分比口径（30.00）
        when(repository.findHighlights(2L)).thenReturn(List.of(
                highlight("PROTEIN", "g", new BigDecimal("21.2000"), "ABSOLUTE", null, new BigDecimal("12.000"), null),
                highlight("POTASSIUM", "mg", new BigDecimal("733.0000"), "NRV_PERCENT", new BigDecimal("30.00"), null,
                        new BigDecimal("36.7"))));

        List<HighlightDto> highlights = service.getFoodDetail(2L).highlights();

        assertThat(highlights)
                .extracting(HighlightDto::ruleLabel)
                .containsExactly("每 100g ≥12g", "每 100g ≥30% NRV");
    }

    @Test
    void normalize_outputsPlainNumberWithoutScientificNotation() {
        stubDetail();
        when(repository.findNutrientTiles(2L)).thenReturn(List.of(
                new NutrientTileRow("ENERGY", "热量", "kcal", "PROXIMATE", new BigDecimal("34.0000"),
                        new BigDecimal("1.7")),
                new NutrientTileRow("FIBER", "膳食纤维", "g", "PROXIMATE", new BigDecimal("2.4000"),
                        new BigDecimal("9.6"))));
        when(repository.findHighlights(2L)).thenReturn(List.of());

        FoodDetailDto detail = service.getFoodDetail(2L);

        assertThat(detail.nutrientTiles())
                .extracting(tile -> tile.amount().toPlainString())
                .containsExactly("34", "2.4");
        // NRV% 由视图 ROUND(...,1) 产出，保持 1 位小数，与接口契约示例一致
        assertThat(detail.nutrientTiles())
                .extracting(tile -> tile.nrvPercent().toPlainString())
                .containsExactly("1.7", "9.6");
        // group 由后端原样透传稳定的分组代码，中文映射在前端完成
        assertThat(detail.nutrientTiles())
                .extracting(tile -> tile.group())
                .containsExactly("PROXIMATE", "PROXIMATE");
    }

    @Test
    void getFoodDetail_returnsNullWhenFoodMissing() {
        when(repository.findFoodDetail(999L)).thenReturn(Optional.empty());

        // 返回 null 而不是抛异常，由 controller 决定 404，避免 service 依赖 Web 层语义
        assertThat(service.getFoodDetail(999L)).isNull();
    }

    @Test
    void getFoodDetail_failsFastWhenRuleStandardMissing() {
        when(repository.findFoodDetail(2L)).thenReturn(Optional.of(APPLE));
        when(repository.findNutrientTiles(2L)).thenReturn(List.of());
        when(repository.findHighlights(2L)).thenReturn(List.of());
        when(repository.findRuleStandard()).thenReturn(Optional.empty());

        // 字典缺行属于配置错误，应当立刻暴露并带上可定位的键，而不是返回 null 让页面渲染空白
        assertThatThrownBy(() -> service.getFoodDetail(2L))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("rule_source.code = GB_28050_2025");
    }

    private void stubDetail() {
        when(repository.findFoodDetail(2L)).thenReturn(Optional.of(APPLE));
        when(repository.findNutrientTiles(2L)).thenReturn(List.of());
        when(repository.findRuleStandard())
                .thenReturn(Optional.of(new RuleStandardRow("GB 28050-2025", LocalDate.of(2027, 3, 16))));
    }

    private static HighlightRow highlight(String code, String unit, BigDecimal amount, String ruleType,
                                          BigDecimal thresholdPercent, BigDecimal thresholdPer100g,
                                          BigDecimal nrvPercent) {
        return new HighlightRow(code, "名称", unit, amount, ruleType, thresholdPercent, thresholdPer100g,
                "判定依据说明", nrvPercent, "生理作用", "MedlinePlus", "https://example.org/source",
                LocalDate.of(2026, 10, 21));
    }
}