package ming.valuesjava.dto;

/**
 * 分类新增/修改请求体。
 * sortOrder 用包装类型，才能把「未传」与「传了 0」区分开，避免默认值掩盖客户端的漏传。
 */
public record CategoryRequest(
        String code,
        String name,
        Integer sortOrder) {
}