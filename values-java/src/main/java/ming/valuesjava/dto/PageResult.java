package ming.valuesjava.dto;

import java.util.List;

/**
 * 通用分页响应。
 * total 用 long：food 的主键是 BIGINT UNSIGNED，行数统计不应受 int 上限约束；
 * totalPages 由「总数 / 每页数」直接算出，前端无需重复推导。
 */
public record PageResult<T>(
        List<T> items,
        long total,
        int page,
        int size,
        int totalPages) {

    public static <T> PageResult<T> of(List<T> items, long total, int page, int size) {
        int totalPages = size <= 0 ? 0 : (int) ((total + size - 1) / size);
        return new PageResult<>(items, total, page, size, totalPages);
    }
}