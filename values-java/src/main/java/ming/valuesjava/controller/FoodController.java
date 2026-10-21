package ming.valuesjava.controller;

import java.util.List;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

import ming.valuesjava.dto.CategoryDto;
import ming.valuesjava.dto.FoodDetailDto;
import ming.valuesjava.dto.FoodSummaryDto;
import ming.valuesjava.service.FoodQueryService;

/**
 * 食物营养百科的只读接口。
 * 全部为 GET，不做写操作，因此不引入鉴权与事务，降低暴露面。
 */
@RestController
@RequestMapping("/api")
public class FoodController {

    private final FoodQueryService foodQueryService;

    public FoodController(FoodQueryService foodQueryService) {
        this.foodQueryService = foodQueryService;
    }

    @GetMapping("/categories")
    public List<CategoryDto> listCategories() {
        return foodQueryService.listCategories();
    }

    @GetMapping("/foods")
    public List<FoodSummaryDto> listFoods() {
        return foodQueryService.listFoods();
    }

    @GetMapping("/foods/{id}")
    public FoodDetailDto getFood(@PathVariable("id") long id) {
        FoodDetailDto detail = foodQueryService.getFoodDetail(id);
        // 资源不存在返回 404，而不是 200 + 空对象，让前端能区分「查不到」与「查询成功但无内容」
        if (detail == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "食物不存在：" + id);
        }
        return detail;
    }
}