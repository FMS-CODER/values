package ming.valuesjava.service;

import java.util.List;

import ming.valuesjava.dto.AdminCategoryDto;
import ming.valuesjava.dto.CategoryRequest;

/**
 * 管理端分类服务。
 * 写操作全部经过这里做校验与引用检查，controller 只负责 HTTP 语义。
 */
public interface CategoryAdminService {

    List<AdminCategoryDto> listCategories();

    AdminCategoryDto createCategory(CategoryRequest request);

    AdminCategoryDto updateCategory(long id, CategoryRequest request);

    void deleteCategory(long id);
}