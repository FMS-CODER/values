package ming.valuesjava.entity;

import java.math.BigDecimal;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

/**
 * food_nutrient 表实体（每 100g 可食部分的营养含量）。
 *
 * amount 与 basis_amount 是 DECIMAL，必须用 BigDecimal；edible_portion 是 TINYINT(1)，
 * 语义为布尔，用 Boolean 承载。主键 id 为 BIGINT AUTO_INCREMENT，用 AUTO。
 */
@TableName("food_nutrient")
public class FoodNutrient {

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    private Long foodId;

    private String nutrientCode;

    private BigDecimal amount;

    private String basisType;

    private BigDecimal basisAmount;

    private Boolean ediblePortion;

    private Integer dataPoints;

    private String derivationCode;

    private Integer sourceId;

    private String sourceRecordId;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
    }

    public Long getFoodId() {
        return foodId;
    }

    public void setFoodId(Long foodId) {
        this.foodId = foodId;
    }

    public String getNutrientCode() {
        return nutrientCode;
    }

    public void setNutrientCode(String nutrientCode) {
        this.nutrientCode = nutrientCode;
    }

    public BigDecimal getAmount() {
        return amount;
    }

    public void setAmount(BigDecimal amount) {
        this.amount = amount;
    }

    public String getBasisType() {
        return basisType;
    }

    public void setBasisType(String basisType) {
        this.basisType = basisType;
    }

    public BigDecimal getBasisAmount() {
        return basisAmount;
    }

    public void setBasisAmount(BigDecimal basisAmount) {
        this.basisAmount = basisAmount;
    }

    public Boolean getEdiblePortion() {
        return ediblePortion;
    }

    public void setEdiblePortion(Boolean ediblePortion) {
        this.ediblePortion = ediblePortion;
    }

    public Integer getDataPoints() {
        return dataPoints;
    }

    public void setDataPoints(Integer dataPoints) {
        this.dataPoints = dataPoints;
    }

    public String getDerivationCode() {
        return derivationCode;
    }

    public void setDerivationCode(String derivationCode) {
        this.derivationCode = derivationCode;
    }

    public Integer getSourceId() {
        return sourceId;
    }

    public void setSourceId(Integer sourceId) {
        this.sourceId = sourceId;
    }

    public String getSourceRecordId() {
        return sourceRecordId;
    }

    public void setSourceRecordId(String sourceRecordId) {
        this.sourceRecordId = sourceRecordId;
    }
}