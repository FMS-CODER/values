package ming.valuesjava.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;

import ming.valuesjava.entity.Food;

/** food 表的基础 CRUD，复杂联表查询见 FoodAdminMapper / FoodQueryMapper */
public interface FoodMapper extends BaseMapper<Food> {
}