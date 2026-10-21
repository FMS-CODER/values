package ming.valuesjava.controller;

import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import ming.valuesjava.dto.AdminCategoryDto;
import ming.valuesjava.dto.CategoryRequest;
import ming.valuesjava.service.CategoryAdminService;

/**
 * 管理端分类接口。
 *
 * 【风险声明】仅本机原型：本组接口没有鉴权，任何能访问 8080 的进程都能增删分类。
 * 之所以仍限制 CORS 来源（见 WebConfig），是为了避免用户浏览任意网页时被脚本代发请求；
 * 但 CORS 不是访问控制，正式部署前必须补登录态与权限校验。
 */
@RestController
@RequestMapping("/api/admin/categories")
public class CategoryAdminController {

    private final CategoryAdminService categoryAdminService;

    public CategoryAdminController(CategoryAdminService categoryAdminService) {
        this.categoryAdminService = categoryAdminService;
    }

    @GetMapping
    public List<AdminCategoryDto> list() {
        return categoryAdminService.listCategories();
    }

    @PostMapping
    public ResponseEntity<AdminCategoryDto> create(@RequestBody(required = false) CategoryRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(categoryAdminService.createCategory(request));
    }

    @PutMapping("/{id}")
    public AdminCategoryDto update(@PathVariable("id") long id,
                                   @RequestBody(required = false) CategoryRequest request) {
        return categoryAdminService.updateCategory(id, request);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable("id") long id) {
        categoryAdminService.deleteCategory(id);
        return ResponseEntity.noContent().build();
    }
}