package ming.valuesjava.repository;

import java.util.List;
import java.util.Optional;

import org.springframework.stereotype.Repository;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;

import ming.valuesjava.entity.Food;
import ming.valuesjava.entity.FoodCategory;
import ming.valuesjava.mapper.CategoryAdminMapper;
import ming.valuesjava.mapper.FoodCategoryMapper;
import ming.valuesjava.mapper.FoodMapper;

/**
 * 管理端分类写操作的数据访问层。
 *
 * 为什么 foodCount 用子查询而不是 LEFT JOIN + GROUP BY：
 * 分类只有十几行，子查询走 idx_food_category 即可，语义也更直观；
 * 排序仍按 sort_order，id 作为次级排序保证 sort_order 相同时也稳定。
 */
@Repository
public class CategoryAdminRepository {

    private final CategoryAdminMapper categoryAdminMapper;
    private final FoodCategoryMapper foodCategoryMapper;
    private final FoodMapper foodMapper;

    public CategoryAdminRepository(CategoryAdminMapper categoryAdminMapper,
                                   FoodCategoryMapper foodCategoryMapper,
                                   FoodMapper foodMapper) {
        this.categoryAdminMapper = categoryAdminMapper;
        this.foodCategoryMapper = foodCategoryMapper;
        this.foodMapper = foodMapper;
    }

    public List<CategoryRow> findAll() {
        return categoryAdminMapper.findAll();
    }

    public Optional<CategoryRow> findById(long id) {
        return Optional.ofNullable(categoryAdminMapper.findById(id));
    }

    public long countDuplicate(String code, String name, long excludeId) {
        Long count = foodCategoryMapper.selectCount(new LambdaQueryWrapper<FoodCategory>()
                .and(wrapper -> wrapper.eq(FoodCategory::getCode, code).or().eq(FoodCategory::getName, name))
                .ne(FoodCategory::getId, excludeId));
        return count == null ? 0 : count;
    }

    public long countFoods(long categoryId) {
        Long count = foodMapper.selectCount(
                new LambdaQueryWrapper<Food>().eq(Food::getCategoryId, categoryId));
        return count == null ? 0 : count;
    }

    /**
     * 主键交给数据库自增：插入后 MyBatis-Plus 把生成值回填到实体，
     * 不再需要先查 MAX(id) 再写入，并发下也不存在抢同一个 id 的问题。
     */
    public long insert(String code, String name, int sortOrder) {
        FoodCategory entity = new FoodCategory();
        entity.setCode(code);
        entity.setName(name);
        entity.setSortOrder(sortOrder);
        foodCategoryMapper.insert(entity);
        return entity.getId();
    }

    public int update(long id, String code, String name, int sortOrder) {
        FoodCategory entity = new FoodCategory();
        entity.setId((int) id);
        entity.setCode(code);
        entity.setName(name);
        entity.setSortOrder(sortOrder);
        return foodCategoryMapper.updateById(entity);
    }

    public int delete(long id) {
        return foodCategoryMapper.deleteById(id);
    }

    public record CategoryRow(long id, String code, String name, int sortOrder, long foodCount) {
    }
}