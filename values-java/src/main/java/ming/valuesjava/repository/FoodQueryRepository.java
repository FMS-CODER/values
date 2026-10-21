package ming.valuesjava.repository;

import java.math.BigDecimal;
import java.sql.Date;
import java.time.LocalDate;
import java.util.List;
import java.util.Optional;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

/**
 * 食物营养百科的只读查询层。
 *
 * 设计取舍：
 * 1. 全部使用显式 SQL + JdbcTemplate，视图已经把 NRV 换算和高亮判定算好，Java 侧只做映射；
 * 2. 返回的是「行」对象（嵌套 record）而不是 DTO，DTO 的组装与文案拼接留在 service 层，
 *    这样 SQL 的口径变化不会牵连接口契约；
 * 3. 数值一律用 BigDecimal，避免 DECIMAL 经过 double 后精度丢失。
 */
@Repository
public class FoodQueryRepository {

    private static final String SQL_CATEGORIES = """
            SELECT code, name, sort_order
            FROM food_category
            ORDER BY sort_order
            """;

    private static final String SQL_FOOD_SUMMARIES = """
            SELECT f.id, f.name, c.code AS category_code, c.name AS category_name, f.image_url, f.description
            FROM food f
            JOIN food_category c ON c.id = f.category_id
            ORDER BY f.id
            """;

    private static final String SQL_CARD_NUTRIENTS = """
            SELECT fn.food_id, ni.code, ni.name, ni.unit, fn.amount
            FROM food_nutrient fn
            JOIN nutrient_info ni ON ni.code = fn.nutrient_code
            WHERE ni.show_in_card = 1 AND fn.basis_type = '100G'
            ORDER BY fn.food_id, ni.sort_order
            """;

    private static final String SQL_FOOD_DETAIL = """
            SELECT f.id, f.name, c.code AS category_code, c.name AS category_name, f.image_url, f.description,
                   f.state, f.claim_note, f.source_record_id, f.verified, f.source_note, ds.name AS source_name
            FROM food f
            JOIN food_category c ON c.id = f.category_id
            JOIN data_source ds ON ds.id = f.source_id
            WHERE f.id = ?
            """;

    private static final String SQL_NUTRIENT_TILES = """
            SELECT nutrient_code, nutrient_name, unit, amount, nrv_percent
            FROM v_food_nutrient_nrv
            WHERE food_id = ?
            ORDER BY sort_order
            """;

    private static final String SQL_HIGHLIGHTS = """
            SELECT nutrient_code, nutrient_name, unit, amount, rich_rule_type, rich_threshold_percent,
                   rich_threshold_per_100g, rule_note, nrv_percent, role, source_name, source_url, verified_at
            FROM v_food_highlight
            WHERE food_id = ?
            ORDER BY sort_order
            """;

    private static final String SQL_RULE_STANDARD = """
            SELECT name, effective_date
            FROM rule_source
            WHERE code = 'GB_28050_2025'
            """;

    private final JdbcTemplate jdbcTemplate;

    public FoodQueryRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public List<CategoryRow> findCategories() {
        return jdbcTemplate.query(SQL_CATEGORIES, CATEGORY_MAPPER);
    }

    public List<FoodSummaryRow> findFoodSummaries() {
        return jdbcTemplate.query(SQL_FOOD_SUMMARIES, FOOD_SUMMARY_MAPPER);
    }

    /**
     * 一次取回所有食物的卡片营养素，service 侧按 food_id 分组，避免逐条食物再查一次的 N+1。
     */
    public List<CardNutrientRow> findCardNutrients() {
        return jdbcTemplate.query(SQL_CARD_NUTRIENTS, CARD_NUTRIENT_MAPPER);
    }

    public Optional<FoodDetailRow> findFoodDetail(long foodId) {
        return jdbcTemplate.query(SQL_FOOD_DETAIL, FOOD_DETAIL_MAPPER, foodId).stream().findFirst();
    }

    public List<NutrientTileRow> findNutrientTiles(long foodId) {
        return jdbcTemplate.query(SQL_NUTRIENT_TILES, NUTRIENT_TILE_MAPPER, foodId);
    }

    public List<HighlightRow> findHighlights(long foodId) {
        return jdbcTemplate.query(SQL_HIGHLIGHTS, HIGHLIGHT_MAPPER, foodId);
    }

    public Optional<RuleStandardRow> findRuleStandard() {
        return jdbcTemplate.query(SQL_RULE_STANDARD, RULE_STANDARD_MAPPER).stream().findFirst();
    }

    // ------------------------------------------------------------------ 行映射

    private static final RowMapper<CategoryRow> CATEGORY_MAPPER = (rs, rowNum) ->
            new CategoryRow(rs.getString("code"), rs.getString("name"), rs.getInt("sort_order"));

    private static final RowMapper<FoodSummaryRow> FOOD_SUMMARY_MAPPER = (rs, rowNum) ->
            new FoodSummaryRow(
                    rs.getLong("id"),
                    rs.getString("name"),
                    rs.getString("category_code"),
                    rs.getString("category_name"),
                    rs.getString("image_url"),
                    rs.getString("description"));

    private static final RowMapper<CardNutrientRow> CARD_NUTRIENT_MAPPER = (rs, rowNum) ->
            new CardNutrientRow(
                    rs.getLong("food_id"),
                    rs.getString("code"),
                    rs.getString("name"),
                    rs.getString("unit"),
                    rs.getBigDecimal("amount"));

    private static final RowMapper<FoodDetailRow> FOOD_DETAIL_MAPPER = (rs, rowNum) ->
            new FoodDetailRow(
                    rs.getLong("id"),
                    rs.getString("name"),
                    rs.getString("category_code"),
                    rs.getString("category_name"),
                    rs.getString("image_url"),
                    rs.getString("description"),
                    rs.getString("state"),
                    rs.getString("claim_note"),
                    rs.getString("source_record_id"),
                    rs.getBoolean("verified"),
                    rs.getString("source_note"),
                    rs.getString("source_name"));

    private static final RowMapper<NutrientTileRow> NUTRIENT_TILE_MAPPER = (rs, rowNum) ->
            new NutrientTileRow(
                    rs.getString("nutrient_code"),
                    rs.getString("nutrient_name"),
                    rs.getString("unit"),
                    rs.getBigDecimal("amount"),
                    rs.getBigDecimal("nrv_percent"));

    private static final RowMapper<HighlightRow> HIGHLIGHT_MAPPER = (rs, rowNum) ->
            new HighlightRow(
                    rs.getString("nutrient_code"),
                    rs.getString("nutrient_name"),
                    rs.getString("unit"),
                    rs.getBigDecimal("amount"),
                    rs.getString("rich_rule_type"),
                    rs.getBigDecimal("rich_threshold_percent"),
                    rs.getBigDecimal("rich_threshold_per_100g"),
                    rs.getString("rule_note"),
                    rs.getBigDecimal("nrv_percent"),
                    rs.getString("role"),
                    rs.getString("source_name"),
                    rs.getString("source_url"),
                    toLocalDate(rs.getDate("verified_at")));

    private static final RowMapper<RuleStandardRow> RULE_STANDARD_MAPPER = (rs, rowNum) ->
            new RuleStandardRow(rs.getString("name"), toLocalDate(rs.getDate("effective_date")));

    private static LocalDate toLocalDate(Date date) {
        return date == null ? null : date.toLocalDate();
    }

    // ------------------------------------------------------------------ 行结构

    public record CategoryRow(String code, String name, int sortOrder) {
    }

    public record FoodSummaryRow(long id, String name, String categoryCode, String categoryName,
                                 String imageUrl, String description) {
    }

    public record CardNutrientRow(long foodId, String code, String name, String unit, BigDecimal amount) {
    }

    public record FoodDetailRow(long id, String name, String categoryCode, String categoryName, String imageUrl,
                                String description, String state, String claimNote, String sourceRecordId,
                                boolean verified, String sourceNote, String sourceName) {
    }

    public record NutrientTileRow(String code, String name, String unit, BigDecimal amount, BigDecimal nrvPercent) {
    }

    public record HighlightRow(String code, String name, String unit, BigDecimal amount, String richRuleType,
                               BigDecimal richThresholdPercent, BigDecimal richThresholdPer100g, String ruleNote,
                               BigDecimal nrvPercent, String role, String sourceName, String sourceUrl,
                               LocalDate verifiedAt) {
    }

    public record RuleStandardRow(String name, LocalDate effectiveDate) {
    }
}