package ming.valuesjava.dto;

import java.util.List;

import com.fasterxml.jackson.annotation.JsonInclude;

/**
 * 图片审核分页响应。
 * hint 只在清单文件缺失时出现：此时属于「还没有数据」而不是「接口坏了」，
 * 用 200 + 提示让前端能引导用户去跑抓图脚本；无提示时不序列化该字段，保持契约干净。
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record AdminImagePageDto(
        List<AdminImageItemDto> items,
        long total,
        int page,
        int size,
        int totalPages,
        String hint) {

    public static AdminImagePageDto of(List<AdminImageItemDto> items, long total, int page, int size) {
        int totalPages = size <= 0 ? 0 : (int) ((total + size - 1) / size);
        return new AdminImagePageDto(items, total, page, size, totalPages, null);
    }

    public static AdminImagePageDto missing(int page, int size, String hint) {
        return new AdminImagePageDto(List.of(), 0, page, size, 0, hint);
    }
}