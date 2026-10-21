package ming.valuesjava.service.impl;

import java.time.format.DateTimeFormatter;
import java.util.ArrayList;
import java.util.List;

import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import ming.valuesjava.common.ApiException;
import ming.valuesjava.dto.AdminFoodDetailDto;
import ming.valuesjava.dto.AdminFoodSummaryDto;
import ming.valuesjava.dto.FoodRequest;
import ming.valuesjava.dto.PageResult;
import ming.valuesjava.repository.FoodAdminRepository;
import ming.valuesjava.repository.FoodAdminRepository.FoodDetailRow;
import ming.valuesjava.repository.FoodAdminRepository.FoodSummaryRow;
import ming.valuesjava.repository.FoodAdminRepository.FoodWriteData;
import ming.valuesjava.service.FoodAdminService;

/**
 * 食物管理实现。
 *
 * 校验口径说明：
 * 1. 食物名称允许重复：USDA 数据里同一名称会对应不同规格/加工方式（如「生」「煮熟」），
 *    强行唯一会挡住正常导入，重复问题交给 fdc_id 这个真正的来源键来约束；
 * 2. fdc_id 仍要求唯一：它是对接 USDA 的幂等键，重复会让后续导入脚本覆盖错行；
 * 3. 文本长度按数据库列宽提前拦截，避免把 DataIntegrityViolation 变成 500。
 */
@Service
public class FoodAdminServiceImpl implements FoodAdminService {

    /** 列表里的更新时间精确到分钟即可，秒级信息对管理页面没有价值，也避免前端做格式化 */
    private static final DateTimeFormatter UPDATED_AT_FORMATTER = DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm");
    private static final DateTimeFormatter DATE_FORMATTER = DateTimeFormatter.ISO_LOCAL_DATE;

    private static final int MAX_NAME_LENGTH = 64;
    private static final int MAX_NAME_EN_LENGTH = 200;
    private static final int MAX_IMAGE_URL_LENGTH = 255;
    private static final int MAX_DESCRIPTION_LENGTH = 255;
    private static final int MAX_STATE_LENGTH = 32;
    private static final int MAX_NOTE_LENGTH = 255;

    private static final int DEFAULT_PAGE_SIZE = 20;
    private static final int MAX_PAGE_SIZE = 100;

    /** 新增时如果既没有来源也没有指定 sourceId，就回落到 USDA_FOUNDATION，与现有数据保持一致 */
    private static final String DEFAULT_SOURCE_CODE = "USDA_FOUNDATION";

    private final FoodAdminRepository foodAdminRepository;

    public FoodAdminServiceImpl(FoodAdminRepository foodAdminRepository) {
        this.foodAdminRepository = foodAdminRepository;
    }

    @Override
    public PageResult<AdminFoodSummaryDto> searchFoods(String keyword, String categoryCode, int page, int size) {
        int safePage = Math.max(page, 1);
        // size 与 page 做归一化而不是报 400：分页参数属于展示细节，前端滚动加载时传 0 或超大值
        // 不应该让整个列表失败，统一夹到合法区间更稳妥
        int safeSize = size <= 0 ? DEFAULT_PAGE_SIZE : Math.min(size, MAX_PAGE_SIZE);
        long offset = (long) (safePage - 1) * safeSize;

        long total = foodAdminRepository.count(keyword, categoryCode);
        List<FoodSummaryRow> rows = offset >= total
                ? List.of()
                : foodAdminRepository.findPage(keyword, categoryCode, safeSize, (int) offset);

        List<AdminFoodSummaryDto> items = new ArrayList<>(rows.size());
        for (FoodSummaryRow row : rows) {
            items.add(new AdminFoodSummaryDto(
                    row.id(),
                    row.name(),
                    row.nameEn(),
                    row.categoryCode(),
                    row.categoryName(),
                    row.imageUrl(),
                    row.description(),
                    row.state(),
                    row.fdcId(),
                    row.verified(),
                    row.updatedAt() == null ? null : UPDATED_AT_FORMATTER.format(row.updatedAt())));
        }
        return PageResult.of(items, total, safePage, safeSize);
    }

    @Override
    public AdminFoodDetailDto getFood(long id) {
        return foodAdminRepository.findDetail(id)
                .map(FoodAdminServiceImpl::toDetailDto)
                .orElseThrow(() -> ApiException.notFound("食物不存在：" + id));
    }

    @Override
    @Transactional
    public AdminFoodDetailDto createFood(FoodRequest request) {
        FoodWriteData data = validateAndNormalize(request, null);
        long id;
        try {
            id = foodAdminRepository.insert(data);
        } catch (DuplicateKeyException ex) {
            // 并发下「先查后写」可能都被放行，唯一索引才是最终防线，这里翻译成与预检查一致的文案
            throw ApiException.conflict("fdcId 已存在");
        }
        return getFood(id);
    }

    @Override
    @Transactional
    public AdminFoodDetailDto updateFood(long id, FoodRequest request) {
        if (!foodAdminRepository.existsFood(id)) {
            throw ApiException.notFound("食物不存在：" + id);
        }
        FoodWriteData data = validateAndNormalize(request, id);
        try {
            foodAdminRepository.update(id, data);
        } catch (DuplicateKeyException ex) {
            throw ApiException.conflict("fdcId 已存在");
        }
        return getFood(id);
    }

    @Override
    @Transactional
    public void deleteFood(long id) {
        // food_nutrient 有 ON DELETE CASCADE，删主表即可；这里不做手动级联，避免与数据库约束重复维护
        if (foodAdminRepository.delete(id) == 0) {
            throw ApiException.notFound("食物不存在：" + id);
        }
    }

    private FoodWriteData validateAndNormalize(FoodRequest request, Long foodId) {
        if (request == null) {
            throw ApiException.badRequest("请求体不能为空");
        }

        String name = trimToNull(request.name());
        if (name == null) {
            throw ApiException.badRequest("name 不能为空");
        }
        if (name.length() > MAX_NAME_LENGTH) {
            throw ApiException.badRequest("name 长度不能超过 " + MAX_NAME_LENGTH);
        }

        String nameEn = optionalText(request.nameEn(), "nameEn", MAX_NAME_EN_LENGTH);

        if (request.categoryId() == null) {
            throw ApiException.badRequest("categoryId 不能为空");
        }
        if (!foodAdminRepository.existsCategory(request.categoryId())) {
            throw ApiException.badRequest("categoryId 不存在：" + request.categoryId());
        }

        String imageUrl = optionalText(request.imageUrl(), "imageUrl", MAX_IMAGE_URL_LENGTH);
        if (imageUrl != null && !imageUrl.startsWith("/")) {
            // 前端直接把它当 img src 使用，必须是站点内绝对路径，否则会触发外链加载或 404
            throw ApiException.badRequest("imageUrl 必须以 / 开头");
        }

        String description = optionalText(request.description(), "description", MAX_DESCRIPTION_LENGTH);
        String state = optionalText(request.state(), "state", MAX_STATE_LENGTH);
        String sourceNote = optionalText(request.sourceNote(), "sourceNote", MAX_NOTE_LENGTH);
        String claimNote = optionalText(request.claimNote(), "claimNote", MAX_NOTE_LENGTH);

        Long fdcId = request.fdcId();
        if (fdcId != null && fdcId <= 0) {
            throw ApiException.badRequest("fdcId 必须为正整数");
        }
        if (foodAdminRepository.fdcIdTaken(fdcId, foodId)) {
            throw ApiException.conflict("fdcId 已存在");
        }

        int sourceId = resolveSourceId(request.sourceId());
        boolean verified = Boolean.TRUE.equals(request.verified());

        return new FoodWriteData(name, nameEn, request.categoryId(), imageUrl, description, state, fdcId,
                sourceId, verified, sourceNote, claimNote);
    }

    private int resolveSourceId(Integer sourceId) {
        if (sourceId == null) {
            return foodAdminRepository.findDataSourceId(DEFAULT_SOURCE_CODE)
                    .orElseThrow(() -> ApiException.internal(
                            "缺少数据来源字典：data_source.code = " + DEFAULT_SOURCE_CODE));
        }
        if (!foodAdminRepository.existsDataSource(sourceId)) {
            throw ApiException.badRequest("sourceId 不存在：" + sourceId);
        }
        return sourceId;
    }

    private static String optionalText(String value, String field, int maxLength) {
        String trimmed = trimToNull(value);
        if (trimmed != null && trimmed.length() > maxLength) {
            throw ApiException.badRequest(field + " 长度不能超过 " + maxLength);
        }
        return trimmed;
    }

    private static String trimToNull(String value) {
        if (value == null) {
            return null;
        }
        String trimmed = value.trim();
        return trimmed.isEmpty() ? null : trimmed;
    }

    private static AdminFoodDetailDto toDetailDto(FoodDetailRow row) {
        return new AdminFoodDetailDto(
                row.id(),
                row.name(),
                row.nameEn(),
                row.categoryId(),
                row.categoryCode(),
                row.categoryName(),
                row.imageUrl(),
                row.description(),
                row.state(),
                row.fdcId(),
                row.ndbNumber(),
                row.dataType(),
                row.publicationDate() == null ? null : DATE_FORMATTER.format(row.publicationDate()),
                row.sourceId(),
                row.sourceName(),
                row.sourceRecordId(),
                row.verified(),
                row.sourceNote(),
                row.claimNote());
    }
}