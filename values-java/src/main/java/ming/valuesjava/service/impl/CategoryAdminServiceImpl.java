package ming.valuesjava.service.impl;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import ming.valuesjava.common.ApiException;
import ming.valuesjava.dto.AdminCategoryDto;
import ming.valuesjava.dto.CategoryRequest;
import ming.valuesjava.repository.CategoryAdminRepository;
import ming.valuesjava.repository.CategoryAdminRepository.CategoryRow;
import ming.valuesjava.service.CategoryAdminService;

/**
 * 分类管理实现。
 *
 * 为什么删除前要先查引用数：
 * food.category_id 有外键且分类是必填项，直接 DELETE 会抛 SQL 异常变成 500；
 * 先统计再返回 409 + 具体数量，前端可以据此提示用户先迁移食物，比数据库报错可读得多。
 *
 * 为什么 code 强制大写：
 * 代码里（筛选、导入脚本的 category_map.json）都以大写 code 作为稳定标识，
 * 允许小写会引入「同一个分类两种写法」的隐患，故在入口统一约束。
 */
@Service
public class CategoryAdminServiceImpl implements CategoryAdminService {

    private static final Pattern CODE_PATTERN = Pattern.compile("^[A-Z][A-Z0-9_]*$");
    private static final int MAX_CODE_LENGTH = 32;
    private static final int MAX_NAME_LENGTH = 32;
    private static final int MIN_SORT_ORDER = 0;
    private static final int MAX_SORT_ORDER = 999;

    private final CategoryAdminRepository categoryAdminRepository;

    public CategoryAdminServiceImpl(CategoryAdminRepository categoryAdminRepository) {
        this.categoryAdminRepository = categoryAdminRepository;
    }

    @Override
    public List<AdminCategoryDto> listCategories() {
        List<AdminCategoryDto> result = new ArrayList<>();
        for (CategoryRow row : categoryAdminRepository.findAll()) {
            result.add(toDto(row));
        }
        return result;
    }

    @Override
    @Transactional
    public AdminCategoryDto createCategory(CategoryRequest request) {
        ValidatedCategory category = validate(request);
        if (categoryAdminRepository.countDuplicate(category.code(), category.name(), 0L) > 0) {
            throw ApiException.conflict("分类编码或名称已存在");
        }
        long id = categoryAdminRepository.insert(category.code(), category.name(), category.sortOrder());
        return findRequired(id);
    }

    @Override
    @Transactional
    public AdminCategoryDto updateCategory(long id, CategoryRequest request) {
        if (categoryAdminRepository.findById(id).isEmpty()) {
            throw ApiException.notFound("分类不存在：" + id);
        }
        ValidatedCategory category = validate(request);
        if (categoryAdminRepository.countDuplicate(category.code(), category.name(), id) > 0) {
            throw ApiException.conflict("分类编码或名称已存在");
        }
        categoryAdminRepository.update(id, category.code(), category.name(), category.sortOrder());
        return findRequired(id);
    }

    @Override
    @Transactional
    public void deleteCategory(long id) {
        if (categoryAdminRepository.findById(id).isEmpty()) {
            throw ApiException.notFound("分类不存在：" + id);
        }
        long foodCount = categoryAdminRepository.countFoods(id);
        if (foodCount > 0) {
            throw ApiException.conflict("该分类下仍有 " + foodCount + " 个食物，无法删除");
        }
        categoryAdminRepository.delete(id);
    }

    private AdminCategoryDto findRequired(long id) {
        return categoryAdminRepository.findById(id)
                .map(CategoryAdminServiceImpl::toDto)
                .orElseThrow(() -> ApiException.internal("分类写入后未能读回：" + id));
    }

    private static AdminCategoryDto toDto(CategoryRow row) {
        return new AdminCategoryDto(row.id(), row.code(), row.name(), row.sortOrder(), row.foodCount());
    }

    private static ValidatedCategory validate(CategoryRequest request) {
        if (request == null) {
            throw ApiException.badRequest("请求体不能为空");
        }
        String code = trimToNull(request.code());
        if (code == null) {
            throw ApiException.badRequest("code 不能为空");
        }
        if (code.length() > MAX_CODE_LENGTH) {
            throw ApiException.badRequest("code 长度不能超过 " + MAX_CODE_LENGTH);
        }
        if (!CODE_PATTERN.matcher(code).matches()) {
            throw ApiException.badRequest("code 只能包含大写字母、数字和下划线，且必须以大写字母开头");
        }

        String name = trimToNull(request.name());
        if (name == null) {
            throw ApiException.badRequest("name 不能为空");
        }
        if (name.length() > MAX_NAME_LENGTH) {
            throw ApiException.badRequest("name 长度不能超过 " + MAX_NAME_LENGTH);
        }

        if (request.sortOrder() == null) {
            throw ApiException.badRequest("sortOrder 不能为空，取值范围 " + MIN_SORT_ORDER + "-" + MAX_SORT_ORDER);
        }
        if (request.sortOrder() < MIN_SORT_ORDER || request.sortOrder() > MAX_SORT_ORDER) {
            throw ApiException.badRequest("sortOrder 取值范围 " + MIN_SORT_ORDER + "-" + MAX_SORT_ORDER);
        }
        return new ValidatedCategory(code, name, request.sortOrder());
    }

    private static String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    private record ValidatedCategory(String code, String name, int sortOrder) {
    }
}