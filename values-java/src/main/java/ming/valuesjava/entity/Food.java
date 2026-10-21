package ming.valuesjava.entity;

import java.time.LocalDate;
import java.time.LocalDateTime;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

/**
 * food 表实体。
 *
 * 为什么主键用 AUTO：food.id 是 BIGINT AUTO_INCREMENT，交给数据库生成才能与既有 116 行
 * 的自增序列保持一致；管理端新增后要立刻回读详情，因此依赖 MyBatis-Plus 回填主键。
 *
 * 为什么列名不逐个写 @TableField：schema 里的列名都是下划线风格（name_en、image_url、
 * source_record_id），与 MyBatis-Plus 默认的 camelToUnderline 转换一一对应，
 * 只在配置里开启 map-underscore-to-camel-case 即可，少一层重复声明就少一处漂移风险。
 */
@TableName("food")
public class Food {

    @TableId(value = "id", type = IdType.AUTO)
    private Long id;

    private String name;

    private String nameEn;

    /** 对应 food_category.id，库中是 TINYINT UNSIGNED，用 Integer 而不是 int：列本身允许为空时也不至于拆箱异常 */
    private Integer categoryId;

    private String imageUrl;

    private String description;

    private String state;

    /** BIGINT UNSIGNED 超过 int 范围，必须用 Long */
    private Long fdcId;

    private String ndbNumber;

    private String dataType;

    private LocalDate publicationDate;

    private Integer sourceId;

    private String sourceRecordId;

    /** TINYINT(1) 语义是布尔，映射成 Boolean 比 Integer 更贴近业务含义 */
    private Boolean verified;

    private String sourceNote;

    private String claimNote;

    /** created_at/updated_at 由数据库默认值与 ON UPDATE 维护，应用侧只读不写 */
    private LocalDateTime createdAt;

    private LocalDateTime updatedAt;

    public Long getId() {
        return id;
    }

    public void setId(Long id) {
        this.id = id;
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

    public Integer getCategoryId() {
        return categoryId;
    }

    public void setCategoryId(Integer categoryId) {
        this.categoryId = categoryId;
    }

    public String getImageUrl() {
        return imageUrl;
    }

    public void setImageUrl(String imageUrl) {
        this.imageUrl = imageUrl;
    }

    public String getDescription() {
        return description;
    }

    public void setDescription(String description) {
        this.description = description;
    }

    public String getState() {
        return state;
    }

    public void setState(String state) {
        this.state = state;
    }

    public Long getFdcId() {
        return fdcId;
    }

    public void setFdcId(Long fdcId) {
        this.fdcId = fdcId;
    }

    public String getNdbNumber() {
        return ndbNumber;
    }

    public void setNdbNumber(String ndbNumber) {
        this.ndbNumber = ndbNumber;
    }

    public String getDataType() {
        return dataType;
    }

    public void setDataType(String dataType) {
        this.dataType = dataType;
    }

    public LocalDate getPublicationDate() {
        return publicationDate;
    }

    public void setPublicationDate(LocalDate publicationDate) {
        this.publicationDate = publicationDate;
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

    public Boolean getVerified() {
        return verified;
    }

    public void setVerified(Boolean verified) {
        this.verified = verified;
    }

    public String getSourceNote() {
        return sourceNote;
    }

    public void setSourceNote(String sourceNote) {
        this.sourceNote = sourceNote;
    }

    public String getClaimNote() {
        return claimNote;
    }

    public void setClaimNote(String claimNote) {
        this.claimNote = claimNote;
    }

    public LocalDateTime getCreatedAt() {
        return createdAt;
    }

    public void setCreatedAt(LocalDateTime createdAt) {
        this.createdAt = createdAt;
    }

    public LocalDateTime getUpdatedAt() {
        return updatedAt;
    }

    public void setUpdatedAt(LocalDateTime updatedAt) {
        this.updatedAt = updatedAt;
    }
}