package ming.valuesjava.service;

import ming.valuesjava.dto.AdminFoodDetailDto;
import ming.valuesjava.dto.AdminFoodSummaryDto;
import ming.valuesjava.dto.FoodRequest;
import ming.valuesjava.dto.PageResult;

/**
 * 管理端食物服务。
 * 分页参数在这里统一归一化，避免不同 controller 入口出现「size=1000 被放行」的差异。
 */
public interface FoodAdminService {

    PageResult<AdminFoodSummaryDto> searchFoods(String keyword, String categoryCode, int page, int size);

    AdminFoodDetailDto getFood(long id);

    AdminFoodDetailDto createFood(FoodRequest request);

    AdminFoodDetailDto updateFood(long id, FoodRequest request);

    void deleteFood(long id);
}