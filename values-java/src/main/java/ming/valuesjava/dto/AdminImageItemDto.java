package ming.valuesjava.dto;

/**
 * 图片审核清单的一行。
 * imageUrl 直接复用 local_path：清单里的 local_path 已经是站点根路径（/foods/xxx.webp），
 * 前端拿到即可当 img src 用，不需要再拼一次目录。
 */
public record AdminImageItemDto(
        Long foodId,
        String foodName,
        String localPath,
        String imageUrl,
        String sourceName,
        String sourceUrl,
        String photographer,
        String license,
        String attribution,
        String downloadStatus,
        String reviewStatus) {
}