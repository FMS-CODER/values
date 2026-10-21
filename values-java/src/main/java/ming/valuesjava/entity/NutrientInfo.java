package ming.valuesjava.entity;

import java.math.BigDecimal;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

/**
 * nutrient_info 表实体（营养素基础表 + 富含判定规则）。
 *
 * 为什么主键是 IdType.INPUT：主键 code 是 VARCHAR 业务编码（如 VITAMIN_C），
 * 表里没有自增列；用 AUTO 会让 MyBatis-Plus 试图回填一个不存在的生成键。
 *
 * 所有 DECIMAL 列一律用 BigDecimal：NRV 换算要参与除法与阈值比较，
 * 用 double 会引入二进制误差，也让「30.00 显示成 30」这类格式化问题更难控制。
 */
@TableName("nutrient_info")
public class NutrientInfo {

    @TableId(value = "code", type = IdType.INPUT)
    private String code;

    private String name;

    private String nameEn;

    private String unit;

    private String nutrientGroup;

    /** USDA nutrient.id 是 BIGINT UNSIGNED，用 Long */
    private Long usdaNutrientId;

    private String usdaNumber;

    private BigDecimal nrvValue;

    private String nrvUnit;

    private BigDecimal nrvConversionFactor;

    private String richRuleType;

    private BigDecimal richThresholdPercent;

    private BigDecimal richThresholdPer100g;

    private Integer ruleSourceId;

    private String ruleNote;

    /** TINYINT(1) 表示「是否出现在列表卡片」，语义是布尔 */
    private Boolean showInCard;

    private Integer sortOrder;

    public String getCode() {
        return code;
    }

    public void setCode(String code) {
        this.code = code;
    }

    public String getName() {
        return name;
    }

    public void setName(String name) {
        this.name = name;
    }

    public String getNameEn() {
        return nameEn;
    }

    public void setNameEn(String nameEn) {
        this.nameEn = nameEn;
    }

    public String getUnit() {
        return unit;
    }

    public void setUnit(String unit) {
        this.unit = unit;
    }

    public String getNutrientGroup() {
        return nutrientGroup;
    }

    public void setNutrientGroup(String nutrientGroup) {
        this.nutrientGroup = nutrientGroup;
    }

    public Long getUsdaNutrientId() {
        return usdaNutrientId;
    }

    public void setUsdaNutrientId(Long usdaNutrientId) {
        this.usdaNutrientId = usdaNutrientId;
    }

    public String getUsdaNumber() {
        return usdaNumber;
    }

    public void setUsdaNumber(String usdaNumber) {
        this.usdaNumber = usdaNumber;
    }

    public BigDecimal getNrvValue() {
        return nrvValue;
    }

    public void setNrvValue(BigDecimal nrvValue) {
        this.nrvValue = nrvValue;
    }

    public String getNrvUnit() {
        return nrvUnit;
    }

    public void setNrvUnit(String nrvUnit) {
        this.nrvUnit = nrvUnit;
    }

    public BigDecimal getNrvConversionFactor() {
        return nrvConversionFactor;
    }

    public void setNrvConversionFactor(BigDecimal nrvConversionFactor) {
        this.nrvConversionFactor = nrvConversionFactor;
    }

    public String getRichRuleType() {
        return richRuleType;
    }

    public void setRichRuleType(String richRuleType) {
        this.richRuleType = richRuleType;
    }

    public BigDecimal getRichThresholdPercent() {
        return richThresholdPercent;
    }

    public void setRichThresholdPercent(BigDecimal richThresholdPercent) {
        this.richThresholdPercent = richThresholdPercent;
    }

    public BigDecimal getRichThresholdPer100g() {
        return richThresholdPer100g;
    }

    public void setRichThresholdPer100g(BigDecimal richThresholdPer100g) {
        this.richThresholdPer100g = richThresholdPer100g;
    }

    public Integer getRuleSourceId() {
        return ruleSourceId;
    }

    public void setRuleSourceId(Integer ruleSourceId) {
        this.ruleSourceId = ruleSourceId;
    }

    public String getRuleNote() {
        return ruleNote;
    }

    public void setRuleNote(String ruleNote) {
        this.ruleNote = ruleNote;
    }

    public Boolean getShowInCard() {
        return showInCard;
    }

    public void setShowInCard(Boolean showInCard) {
        this.showInCard = showInCard;
    }

    public Integer getSortOrder() {
        return sortOrder;
    }

    public void setSortOrder(Integer sortOrder) {
        this.sortOrder = sortOrder;
    }
}