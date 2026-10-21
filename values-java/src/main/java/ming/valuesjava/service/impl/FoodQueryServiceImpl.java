package ming.valuesjava.service.impl;

import java.math.BigDecimal;
import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.springframework.stereotype.Service;

import ming.valuesjava.dto.CategoryDto;
import ming.valuesjava.dto.FoodDetailDto;
import ming.valuesjava.dto.FoodSummaryDto;
import ming.valuesjava.dto.HighlightDto;
import ming.valuesjava.dto.NutrientAmountDto;
import ming.valuesjava.dto.NutrientTileDto;
import ming.valuesjava.dto.RuleStandardDto;
import ming.valuesjava.dto.SourceDto;
import ming.valuesjava.repository.FoodQueryRepository;
import ming.valuesjava.repository.FoodQueryRepository.CardNutrientRow;
import ming.valuesjava.repository.FoodQueryRepository.CategoryRow;
import ming.valuesjava.repository.FoodQueryRepository.FoodDetailRow;
import ming.valuesjava.repository.FoodQueryRepository.FoodSummaryRow;
import ming.valuesjava.repository.FoodQueryRepository.HighlightRow;
import ming.valuesjava.repository.FoodQueryRepository.NutrientTileRow;
import ming.valuesjava.repository.FoodQueryRepository.RuleStandardRow;
import ming.valuesjava.service.FoodQueryService;

/**
 * 查询编排层实现：把数据库行组装成前端契约要求的 DTO，并负责把规则阈值格式化成可读文案。
 *
 * 为什么文案放后端拼：
 * 「每 100g ≥30% NRV」这类表述依赖规则类型与阈值口径，只有后端同时掌握 rich_rule_type 与阈值；
 * 放在这里可以保证同一规则在列表、详情、分享等所有出口写法一致。
 */
@Service
public class FoodQueryServiceImpl implements FoodQueryService {

    /** 输出日期时统一用 ISO 格式，避免前端再处理时区或本地化差异。 */
    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ISO_LOCAL_DATE;

    private final FoodQueryRepository foodQueryRepository;

    public FoodQueryServiceImpl(FoodQueryRepository foodQueryRepository) {
        this.foodQueryRepository = foodQueryRepository;
    }

    @Override
    public List<CategoryDto> listCategories() {
        List<CategoryDto> result = new ArrayList<>();
        for (CategoryRow row : foodQueryRepository.findCategories()) {
            result.add(new CategoryDto(row.code(), row.name(), row.sortOrder()));
        }
        return result;
    }

    @Override
    public List<FoodSummaryDto> listFoods() {
        List<FoodSummaryRow> foods = foodQueryRepository.findFoodSummaries();
        // 先按 food_id 把卡片营养素归组，避免对每条食物再发起一次查询（N+1）
        // normalize 已处理 null（缺项槽位），全程保持 BigDecimal 引用类型，不做自动拆箱
        Map<Long, List<NutrientAmountDto>> nutrientsByFood = new HashMap<>();
        for (CardNutrientRow row : foodQueryRepository.findCardNutrients()) {
            nutrientsByFood
                    .computeIfAbsent(row.foodId(), key -> new ArrayList<>())
                    .add(new NutrientAmountDto(row.code(), row.name(), row.unit(), normalize(row.amount())));
        }

        List<FoodSummaryDto> result = new ArrayList<>(foods.size());
        for (FoodSummaryRow food : foods) {
            List<NutrientAmountDto> nutrients =
                    nutrientsByFood.getOrDefault(food.id(), List.of());
            result.add(new FoodSummaryDto(
                    food.id(),
                    food.name(),
                    food.categoryCode(),
                    food.categoryName(),
                    food.imageUrl(),
                    food.description(),
                    nutrients));
        }
        return result;
    }

    @Override
    public FoodDetailDto getFoodDetail(long foodId) {
        FoodDetailRow food = foodQueryRepository.findFoodDetail(foodId).orElse(null);
        // 不存在时返回 null，由 controller 决定 HTTP 语义（404），保持 service 不依赖 Web 层类型
        if (food == null) {
            return null;
        }

        List<NutrientTileDto> tiles = new ArrayList<>();
        for (NutrientTileRow row : foodQueryRepository.findNutrientTiles(foodId)) {
            tiles.add(new NutrientTileDto(
                    row.code(),
                    row.name(),
                    row.unit(),
                    // group 只做透传：后端不拼中文组名，顺序与文案由前端按 PROXIMATE/VITAMIN/MINERAL/FATTY_ACID 映射
                    row.group(),
                    normalize(row.amount()),
                    // nrvPercent 由视图 ROUND(...,1) 得到，本身就是 1 位小数（如 41.0），保持原样与契约示例一致
                    row.nrvPercent()));
        }

        List<HighlightDto> highlights = new ArrayList<>();
        for (HighlightRow row : foodQueryRepository.findHighlights(foodId)) {
            highlights.add(new HighlightDto(
                    row.code(),
                    row.name(),
                    row.unit(),
                    normalize(row.amount()),
                    row.nrvPercent(),
                    buildRuleLabel(row),
                    row.ruleNote(),
                    row.role(),
                    row.sourceName(),
                    row.sourceUrl(),
                    row.verifiedAt() == null ? null : DATE_FORMATTER.format(row.verifiedAt())));
        }

        // 判定依据是接口契约的一部分（前端会直接展示标准名），字典缺失属于配置错误；
        // 这里快速失败并给出可定位的信息，比返回 null 让页面渲染出空白更容易排查
        RuleStandardRow ruleStandard = foodQueryRepository.findRuleStandard()
                .orElseThrow(() -> new IllegalStateException(
                        "缺少判定依据字典：rule_source.code = GB_28050_2025"));

        return new FoodDetailDto(
                food.id(),
                food.name(),
                food.categoryCode(),
                food.categoryName(),
                food.imageUrl(),
                food.description(),
                food.state(),
                food.claimNote(),
                new SourceDto(food.sourceName(), food.sourceRecordId(), food.verified(), food.sourceNote()),
                new RuleStandardDto(
                        ruleStandard.name(),
                        ruleStandard.effectiveDate() == null
                                ? null
                                : DATE_FORMATTER.format(ruleStandard.effectiveDate())),
                tiles,
                highlights);
    }

    /**
     * 按规则类型生成判定文案：
     * NRV_PERCENT → 「每 100g ≥{阈值}% NRV」；ABSOLUTE → 「每 100g ≥{阈值}{单位}」。
     * 阈值列在库里是 DECIMAL（30.00、12.000），必须先去掉末尾零再输出，否则会显示成 30.00%。
     */
    private static String buildRuleLabel(HighlightRow row) {
        if ("NRV_PERCENT".equals(row.richRuleType())) {
            return "每 100g ≥" + plain(row.richThresholdPercent()) + "% NRV";
        }
        if ("ABSOLUTE".equals(row.richRuleType())) {
            return "每 100g ≥" + plain(row.richThresholdPer100g()) + row.unit();
        }
        return null;
    }

    private static String plain(BigDecimal value) {
        return value == null ? null : value.stripTrailingZeros().toPlainString();
    }

    /**
     * 归一化 DECIMAL 数值：
     * 数据库返回的是 34.0000 这类定标值，直接序列化会输出多余小数；
     * stripTrailingZeros 对整数可能得到负标度（3.4E+1），再 setScale(0) 转回普通写法，避免 JSON 出现科学计数法。
     */
    private static BigDecimal normalize(BigDecimal value) {
        if (value == null) {
            return null;
        }
        BigDecimal stripped = value.stripTrailingZeros();
        return stripped.scale() < 0 ? stripped.setScale(0) : stripped;
    }
}