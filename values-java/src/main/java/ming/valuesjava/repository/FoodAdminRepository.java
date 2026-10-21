package ming.valuesjava.repository;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Locale;
import java.util.Optional;

import org.springframework.stereotype.Repository;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;

import ming.valuesjava.entity.DataSourceEntity;
import ming.valuesjava.entity.Food;
import ming.valuesjava.entity.FoodCategory;
import ming.valuesjava.mapper.DataSourceMapper;
import ming.valuesjava.mapper.FoodAdminMapper;
import ming.valuesjava.mapper.FoodCategoryMapper;
import ming.valuesjava.mapper.FoodMapper;

/**
 * 管理端食物写操作的数据访问层。
 *
 * 设计取舍：
 * 1. 联表分页与详情放 XML（FoodAdminMapper），单表的判存、查重、增删改用 BaseMapper + LambdaQueryWrapper，
 *    避免为简单条件再写一份 SQL；
 * 2. fdc_id 的唯一性先查后写，用于给出 409 的业务文案；数据库唯一索引仍然是最终防线，
 *    service 会再兜住 DuplicateKeyException，避免并发下变成 500；
 * 3. 明细查询同时连接分类与来源字典，让编辑表单一次拿到展示所需的名称。
 */
@Repository
public class FoodAdminRepository {

    private final FoodAdminMapper foodAdminMapper;
    private final FoodMapper foodMapper;
    private final FoodCategoryMapper foodCategoryMapper;
    private final DataSourceMapper dataSourceMapper;

    public FoodAdminRepository(FoodAdminMapper foodAdminMapper,
                               FoodMapper foodMapper,
                               FoodCategoryMapper foodCategoryMapper,
                               DataSourceMapper dataSourceMapper) {
        this.foodAdminMapper = foodAdminMapper;
        this.foodMapper = foodMapper;
        this.foodCategoryMapper = foodCategoryMapper;
        this.dataSourceMapper = dataSourceMapper;
    }

    public List<FoodSummaryRow> findPage(String keyword, String categoryCode, int limit, int offset) {
        return foodAdminMapper.findPage(keywordPattern(keyword), blankToNull(categoryCode), limit, offset);
    }

    public long count(String keyword, String categoryCode) {
        return foodAdminMapper.count(keywordPattern(keyword), blankToNull(categoryCode));
    }

    public Optional<FoodDetailRow> findDetail(long id) {
        return Optional.ofNullable(foodAdminMapper.findDetail(id));
    }

    public boolean existsFood(long id) {
        Long count = foodMapper.selectCount(
                new LambdaQueryWrapper<Food>().eq(Food::getId, id));
        return count != null && count > 0;
    }

    public boolean existsCategory(long categoryId) {
        Long count = foodCategoryMapper.selectCount(
                new LambdaQueryWrapper<FoodCategory>().eq(FoodCategory::getId, categoryId));
        return count != null && count > 0;
    }

    public Optional<Integer> findDataSourceId(String code) {
        DataSourceEntity row = dataSourceMapper.selectOne(
                new LambdaQueryWrapper<DataSourceEntity>().eq(DataSourceEntity::getCode, code));
        return Optional.ofNullable(row).map(DataSourceEntity::getId);
    }

    public boolean existsDataSource(int sourceId) {
        Long count = dataSourceMapper.selectCount(
                new LambdaQueryWrapper<DataSourceEntity>().eq(DataSourceEntity::getId, sourceId));
        return count != null && count > 0;
    }

    public boolean fdcIdTaken(Long fdcId, Long excludeFoodId) {
        if (fdcId == null) {
            return false;
        }
        // 新增时没有要排除的行，用 0 占位：food.id 是自增主键，永远不会等于 0
        long exclude = excludeFoodId == null ? 0L : excludeFoodId;
        Long count = foodMapper.selectCount(new LambdaQueryWrapper<Food>()
                .eq(Food::getFdcId, fdcId)
                .ne(Food::getId, exclude));
        return count != null && count > 0;
    }

    /**
     * 单表插入交给 BaseMapper：id 是 AUTO_INCREMENT，主键会回填到实体上，
     * 不需要再像 GeneratedKeyHolder 那样手工取生成键。
     */
    public long insert(FoodWriteData data) {
        Food entity = new Food();
        entity.setName(data.name());
        entity.setNameEn(data.nameEn());
        entity.setCategoryId((int) data.categoryId());
        entity.setImageUrl(data.imageUrl());
        entity.setDescription(data.description());
        entity.setState(data.state());
        entity.setFdcId(data.fdcId());
        entity.setSourceId(data.sourceId());
        entity.setVerified(data.verified());
        entity.setSourceNote(data.sourceNote());
        entity.setClaimNote(data.claimNote());
        foodMapper.insert(entity);
        Long id = entity.getId();
        if (id == null) {
            throw new IllegalStateException("新增食物后未能取得自增主键");
        }
        return id;
    }

    public int update(long id, FoodWriteData data) {
        return foodAdminMapper.updateFood(id, data.name(), data.nameEn(), data.categoryId(), data.imageUrl(),
                data.description(), data.state(), data.fdcId(), data.sourceId(), data.verified(),
                data.sourceNote(), data.claimNote());
    }

    public int delete(long id) {
        return foodMapper.deleteById(id);
    }

    /**
     * 关键词按 LIKE 模糊匹配 name/name_en。LOWER 两侧都做，保证与 MySQL 排序规则无关地不区分大小写；
     * 用 '!' 作为转义符，用户输入的 % 和 _ 会按字面量匹配，避免关键词里的百分号把整表捞出来。
     * 转义必须在进 SQL 前完成：MyBatis 的 LIKE 不会自动处理通配符。
     */
    private static String keywordPattern(String keyword) {
        if (keyword == null || keyword.isBlank()) {
            return null;
        }
        return "%" + escapeLike(keyword.trim().toLowerCase(Locale.ROOT)) + "%";
    }

    private static String escapeLike(String value) {
        return value.replace("!", "!!").replace("%", "!%").replace("_", "!_");
    }

    private static String blankToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    public record FoodSummaryRow(long id, String name, String nameEn, String categoryCode, String categoryName,
                                 String imageUrl, String description, String state, Long fdcId, boolean verified,
                                 LocalDateTime updatedAt) {
    }

    public record FoodDetailRow(long id, String name, String nameEn, long categoryId, String categoryCode,
                                String categoryName, String imageUrl, String description, String state, Long fdcId,
                                String ndbNumber, String dataType, LocalDate publicationDate, int sourceId,
                                String sourceName, String sourceRecordId, boolean verified, String sourceNote,
                                String claimNote) {
    }

    /** 写入参数：service 完成校验与默认值填充后的最终值，repository 不再做业务判断 */
    public record FoodWriteData(String name, String nameEn, long categoryId, String imageUrl, String description,
                                String state, Long fdcId, int sourceId, boolean verified, String sourceNote,
                                String claimNote) {
    }
}