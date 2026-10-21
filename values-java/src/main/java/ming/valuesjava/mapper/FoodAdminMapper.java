package ming.valuesjava.mapper;

import java.util.List;

import org.apache.ibatis.annotations.Param;

import ming.valuesjava.repository.FoodAdminRepository.FoodDetailRow;
import ming.valuesjava.repository.FoodAdminRepository.FoodSummaryRow;

/**
 * 管理端食物查询/更新的 Mapper。
 *
 * 为什么列表与计数各写一条 XML：仓储层保留 (limit, offset) 契约，service 也分别调用
 * count 与 findPage；两条语句共用同一个 where 片段，保证 total 与 items 的过滤条件绝对一致。
 * 单表的按 id 判存、fdc_id 查重等简单查询则走 BaseMapper，不需要写 SQL。
 */
public interface FoodAdminMapper {

    List<FoodSummaryRow> findPage(@Param("keywordPattern") String keywordPattern,
                                  @Param("categoryCode") String categoryCode,
                                  @Param("limit") int limit,
                                  @Param("offset") int offset);

    long count(@Param("keywordPattern") String keywordPattern,
               @Param("categoryCode") String categoryCode);

    FoodDetailRow findDetail(@Param("id") long id);

    /**
     * 全字段更新。这里刻意不用 updateById：管理端允许把 image_url、fdc_id 等字段清空，
     * 而 updateById 默认忽略 null，会把「清空」变成「保持原值」，与改造前的显式 SQL 行为不一致。
     * source_record_id / data_type 由导入流程维护，故不在更新列里。
     */
    int updateFood(@Param("id") long id,
                   @Param("name") String name,
                   @Param("nameEn") String nameEn,
                   @Param("categoryId") long categoryId,
                   @Param("imageUrl") String imageUrl,
                   @Param("description") String description,
                   @Param("state") String state,
                   @Param("fdcId") Long fdcId,
                   @Param("sourceId") int sourceId,
                   @Param("verified") boolean verified,
                   @Param("sourceNote") String sourceNote,
                   @Param("claimNote") String claimNote);
}