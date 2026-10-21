package ming.valuesjava.controller;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import ming.valuesjava.dto.AdminFoodDetailDto;
import ming.valuesjava.dto.AdminFoodSummaryDto;
import ming.valuesjava.dto.FoodRequest;
import ming.valuesjava.dto.PageResult;
import ming.valuesjava.service.FoodAdminService;

/**
 * 管理端食物接口。
 *
 * 【风险声明】仅本机原型：未鉴权，写接口可直接改库。
 * 删除依赖 food_nutrient 的 ON DELETE CASCADE，因此这里不再逐个删营养行，
 * 既少一次往返，也避免应用层与数据库约束两套逻辑不一致。
 */
@RestController
@RequestMapping("/api/admin/foods")
public class FoodAdminController {

    private final FoodAdminService foodAdminService;

    public FoodAdminController(FoodAdminService foodAdminService) {
        this.foodAdminService = foodAdminService;
    }

    @GetMapping
    public PageResult<AdminFoodSummaryDto> list(
            @RequestParam(name = "keyword", required = false) String keyword,
            @RequestParam(name = "categoryCode", required = false) String categoryCode,
            @RequestParam(name = "page", defaultValue = "1") int page,
            @RequestParam(name = "size", defaultValue = "20") int size) {
        return foodAdminService.searchFoods(keyword, categoryCode, page, size);
    }

    @GetMapping("/{id}")
    public AdminFoodDetailDto detail(@PathVariable("id") long id) {
        return foodAdminService.getFood(id);
    }

    @PostMapping
    public ResponseEntity<AdminFoodDetailDto> create(@RequestBody(required = false) FoodRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(foodAdminService.createFood(request));
    }

    @PutMapping("/{id}")
    public AdminFoodDetailDto update(@PathVariable("id") long id,
                                     @RequestBody(required = false) FoodRequest request) {
        return foodAdminService.updateFood(id, request);
    }

    @DeleteMapping("/{id}")
    public ResponseEntity<Void> delete(@PathVariable("id") long id) {
        foodAdminService.deleteFood(id);
        return ResponseEntity.noContent().build();
    }
}