package ming.valuesjava.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PatchMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import ming.valuesjava.dto.AdminImageItemDto;
import ming.valuesjava.dto.AdminImagePageDto;
import ming.valuesjava.dto.ImageReviewRequest;
import ming.valuesjava.service.ImageManifestService;

/**
 * 图片审核接口。
 *
 * 【风险声明】仅本机原型：未鉴权，能改清单里的 review_status。
 * 审核结果直接写回 values-python 维护的 CSV，而不是数据库：
 * 清单是抓图脚本的产物，Python 侧按它决定后续处理，数据库里没有对应结构。
 */
@RestController
@RequestMapping("/api/admin/images")
public class ImageAdminController {

    private final ImageManifestService imageManifestService;

    public ImageAdminController(ImageManifestService imageManifestService) {
        this.imageManifestService = imageManifestService;
    }

    @GetMapping
    public AdminImagePageDto list(
            @RequestParam(name = "status", defaultValue = "pending") String status,
            @RequestParam(name = "keyword", required = false) String keyword,
            @RequestParam(name = "page", defaultValue = "1") int page,
            @RequestParam(name = "size", defaultValue = "24") int size) {
        return imageManifestService.listImages(status, keyword, page, size);
    }

    @PatchMapping("/{foodId}/review")
    public AdminImageItemDto review(@PathVariable("foodId") long foodId,
                                    @RequestBody(required = false) ImageReviewRequest request) {
        return imageManifestService.review(foodId, request == null ? null : request.status());
    }
}