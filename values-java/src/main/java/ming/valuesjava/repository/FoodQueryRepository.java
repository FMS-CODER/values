package ming.valuesjava.repository;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

import org.springframework.stereotype.Repository;

import ming.valuesjava.mapper.FoodQueryMapper;

/**
 * 食物营养百科的只读查询层。
 *
 * 设计取舍：
 * 1. 联表与视图查询集中在 FoodQueryMapper.xml，视图已经把 NRV 换算和高亮判定算好，
 *    Java 侧只做映射；SQL 里的口径变化不会牵连接口契约；
 * 2. 返回的仍是「行」对象（嵌套 record）而不是 DTO：DTO 的组装与文案拼接留在 service 层。
 *    改用 MyBatis-Plus 后这些 record 原样保留——它们是不可变的 SQL 投影，
 *    通过 XML 的 resultMap constructor 直接构造，service 与单测都无需改动；
 * 3. 数值一律用 BigDecimal，避免 DECIMAL 经过 double 后精度丢失。
 */
@Repository
public class FoodQueryRepository {

    private final FoodQueryMapper foodQueryMapper;

    public FoodQueryRepository(FoodQueryMapper foodQueryMapper) {
        this.foodQueryMapper = foodQueryMapper;
    }

    public List<CategoryRow> findCategories() {
        return foodQueryMapper.findCategories();
    }

    public List<FoodSummaryRow> findFoodSummaries() {
        return foodQueryMapper.findFoodSummaries();
    }

    /**
     * 一次取回所有食物的卡片营养素，service 侧按 food_id 分组，避免逐条食物再查一次的 N+1。
     */
    public List<CardNutrientRow> findCardNutrients() {
        return foodQueryMapper.findCardNutrients();
    }

    /** Mapper 的 selectOne 在无结果时返回 null，这里统一转成 Optional，保持原有调用契约 */
    public Optional<FoodDetailRow> findFoodDetail(long foodId) {
        return Optional.ofNullable(foodQueryMapper.findFoodDetail(foodId));
    }

    public List<NutrientTileRow> findNutrientTiles(long foodId) {
        return foodQueryMapper.findNutrientTiles(foodId);
    }

    public List<HighlightRow> findHighlights(long foodId) {
        return foodQueryMapper.findHighlights(foodId);
    }

    public Optional<RuleStandardRow> findRuleStandard() {
        return Optional.ofNullable(foodQueryMapper.findRuleStandard());
    }

    // ------------------------------------------------------------------ 行结构

    public record CategoryRow(String code, String name, int sortOrder) {
    }

    public record FoodSummaryRow(long id, String name, String categoryCode, String categoryName,
                                 String imageUrl, String description) {
    }

    /** 卡片营养素行：amount 可能为 null（该食物缺这一项），故用可空的 BigDecimal 承载。 */
    public record CardNutrientRow(long foodId, String code, String name, String unit, BigDecimal amount) {
    }

    public record FoodDetailRow(long id, String name, String categoryCode, String categoryName, String imageUrl,
                                String description, String state, String claimNote, String sourceRecordId,
                                boolean verified, String sourceNote, String sourceName) {
    }

    /**
     * 详情页营养格行。group 是稳定的分组代码（PROXIMATE/VITAMIN/MINERAL/FATTY_ACID），
     * 后端不拼中文组名，交由前端映射展示文案，避免多出口出现不统一的叫法。
     */
    public record NutrientTileRow(String code, String name, String unit, String group, BigDecimal amount,
                                  BigDecimal nrvPercent) {
    }

    public record HighlightRow(String code, String name, String unit, BigDecimal amount, String richRuleType,
                               BigDecimal richThresholdPercent, BigDecimal richThresholdPer100g, String ruleNote,
                               BigDecimal nrvPercent, String role, String sourceName, String sourceUrl,
                               LocalDate verifiedAt) {
    }

    public record RuleStandardRow(String name, LocalDate effectiveDate) {
    }
}