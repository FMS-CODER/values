package ming.valuesjava.entity;

import java.time.LocalDate;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

/**
 * nutrient_knowledge 表实体（营养素科普内容与来源）。
 *
 * 主键 nutrient_code 是 VARCHAR 且与 nutrient_info.code 一对一，没有自增列，故用 IdType.INPUT。
 * verified_at 是 DATE，用 LocalDate 承载，保持与接口里的 ISO 日期格式一致。
 */
@TableName("nutrient_knowledge")
public class NutrientKnowledge {

    @TableId(value = "nutrient_code", type = IdType.INPUT)
    private String nutrientCode;

    private String role;

    private String sourceName;

    private String sourceUrl;

    private LocalDate verifiedAt;

    public String getNutrientCode() {
        return nutrientCode;
    }

    public void setNutrientCode(String nutrientCode) {
        this.nutrientCode = nutrientCode;
    }

    public String getRole() {
        return role;
    }

    public void setRole(String role) {
        this.role = role;
    }

    public String getSourceName() {
        return sourceName;
    }

    public void setSourceName(String sourceName) {
        this.sourceName = sourceName;
    }

    public String getSourceUrl() {
        return sourceUrl;
    }

    public void setSourceUrl(String sourceUrl) {
        this.sourceUrl = sourceUrl;
    }

    public LocalDate getVerifiedAt() {
        return verifiedAt;
    }

    public void setVerifiedAt(LocalDate verifiedAt) {
        this.verifiedAt = verifiedAt;
    }
}