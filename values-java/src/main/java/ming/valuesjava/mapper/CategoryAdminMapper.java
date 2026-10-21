package ming.valuesjava.mapper;

import java.util.List;

import org.apache.ibatis.annotations.Param;

import ming.valuesjava.repository.CategoryAdminRepository.CategoryRow;

/**
 * 管理端分类列表 Mapper。
 *
 * foodCount 用相关子查询而不是 LEFT JOIN + GROUP BY：分类只有十几行，
 * 子查询走 idx_food_category 即可，语义也更直观；
 * 单表的增删改与查重交给 BaseMapper 的 Wrapper 完成。
 */
public interface CategoryAdminMapper {

    List<CategoryRow> findAll();

    CategoryRow findById(@Param("id") long id);
}