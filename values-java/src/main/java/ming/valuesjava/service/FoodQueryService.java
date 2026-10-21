package ming.valuesjava.service;

import java.util.List;

import ming.valuesjava.dto.CategoryDto;
import ming.valuesjava.dto.FoodDetailDto;
import ming.valuesjava.dto.FoodSummaryDto;

/**
 * 食物营养百科的查询服务。
 *
 * 为什么抽出接口：
 * controller 只应该依赖业务语义，不关心数据是查库、走缓存还是调远程接口；
 * 接口把「数据库行对象、规则阈值拼接」这些实现细节挡在下面，
 * 将来替换实现（例如加一层缓存）时 controller 不需要改动。
 */
public interface FoodQueryService {

    /** 查询食物分类，按展示顺序返回，供筛选按钮使用 */
    List<CategoryDto> listCategories();

    /** 查询列表页需要的食物卡片数据，包含卡片上展示的四项营养 */
    List<FoodSummaryDto> listFoods();

    /**
     * 查询单个食物的完整详情。
     * 食物不存在时返回 null，由 controller 决定 HTTP 语义（404），避免 service 依赖 Web 层类型。
     */
    FoodDetailDto getFoodDetail(long foodId);
}