package ming.valuesjava.service;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.nio.file.StandardCopyOption;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import ming.valuesjava.common.ApiException;
import ming.valuesjava.dto.AdminImageItemDto;
import ming.valuesjava.dto.AdminImagePageDto;

/**
 * 图片审核清单服务（数据源是 values-python 维护的 CSV，不是数据库表）。
 *
 * 为什么自己写 CSV 解析而不用 split(",")：
 * attribution/license 这类字段经常是「作者 / 平台 / 许可」这种带逗号的中文句子，
 * 文件里已经用双引号包裹并可能出现 "" 转义；按逗号切会把一行拆成错位的列，
 * 一旦写回就会破坏整份清单。这里实现最小 RFC4180 解析，并在写回时按需加引号。
 *
 * 为什么读写都要加锁：
 * 清单是单文件，多个审核请求并发时「读-改-写」会互相覆盖；
 * 用进程内锁把临界区串起来即可，本原型只有单实例。
 *
 * 为什么路径用相对进程工作目录解析：
 * 前端/后端都从项目根目录启动，配置里写 ../values-python/... 更直观；
 * 绝对路径同样支持，因为 toAbsolutePath 对绝对路径是空操作。
 */
@Service
public class ImageManifestService {

    private static final Logger log = LoggerFactory.getLogger(ImageManifestService.class);

    /** 清单缺失属于「还没抓图」，不是接口故障；GET 返回 200 + 该提示，写操作返回 409 */
    public static final String MISSING_HINT =
            "图片清单不存在，请先在 values-python 目录执行：python -m food_nutrition images-fetch";

    private static final String STATUS_PENDING = "pending";
    private static final String STATUS_APPROVED = "approved";
    private static final String STATUS_REJECTED = "rejected";
    private static final String STATUS_ALL = "all";

    private static final Set<String> FILTER_STATUSES =
            Set.of(STATUS_PENDING, STATUS_APPROVED, STATUS_REJECTED, STATUS_ALL);
    private static final Set<String> REVIEW_STATUSES = Set.of(STATUS_APPROVED, STATUS_REJECTED);

    private static final String COL_FOOD_ID = "food_id";
    private static final String COL_FOOD_NAME = "food_name";
    private static final String COL_LOCAL_PATH = "local_path";
    private static final String COL_SOURCE_NAME = "source_name";
    private static final String COL_SOURCE_URL = "source_url";
    private static final String COL_PHOTOGRAPHER = "photographer";
    private static final String COL_LICENSE = "license";
    private static final String COL_ATTRIBUTION = "attribution";
    private static final String COL_DOWNLOAD_STATUS = "download_status";
    private static final String COL_REVIEW_STATUS = "review_status";

    /** 表头顺序由 Python 脚本固定，这里按列名定位，避免脚本以后调整列序就把写回写错列 */
    private static final List<String> REQUIRED_COLUMNS = List.of(
            COL_FOOD_ID, COL_FOOD_NAME, COL_LOCAL_PATH, COL_SOURCE_NAME, COL_SOURCE_URL,
            COL_PHOTOGRAPHER, COL_LICENSE, COL_ATTRIBUTION, COL_DOWNLOAD_STATUS, COL_REVIEW_STATUS);

    private static final int DEFAULT_PAGE_SIZE = 24;
    private static final int MAX_PAGE_SIZE = 100;

    private final Path manifestPath;

    /** 单实例原型用对象锁即可；换成多实例部署时这里要改成文件锁或数据库 */
    private final Object fileLock = new Object();

    public ImageManifestService(@Value("${app.image.manifest-path}") String manifestPath) {
        this.manifestPath = Paths.get(manifestPath).toAbsolutePath().normalize();
    }

    public AdminImagePageDto listImages(String status, String keyword, int page, int size) {
        int safePage = Math.max(page, 1);
        int safeSize = size <= 0 ? DEFAULT_PAGE_SIZE : Math.min(size, MAX_PAGE_SIZE);
        String filter = normalizeFilterStatus(status);

        synchronized (fileLock) {
            if (!Files.isRegularFile(manifestPath)) {
                log.debug("图片清单不存在，返回空列表 path={}", manifestPath);
                return AdminImagePageDto.missing(safePage, safeSize, MISSING_HINT);
            }

            Manifest manifest = readManifest();
            String normalizedKeyword = keyword == null ? "" : keyword.trim().toLowerCase(Locale.ROOT);
            List<AdminImageItemDto> matched = new ArrayList<>();
            for (CsvRecord record : manifest.dataRecords()) {
                Long foodId = parseFoodId(cell(record, manifest.columns(), COL_FOOD_ID));
                if (foodId == null) {
                    // 清单里可能有手写坏行，跳过比让整个审核页 500 更有用
                    log.warn("图片清单存在无法解析的 food_id，已跳过 row={}", record.values());
                    continue;
                }
                AdminImageItemDto item = toItem(foodId, record, manifest.columns());
                if (!STATUS_ALL.equals(filter) && !filter.equalsIgnoreCase(item.reviewStatus())) {
                    continue;
                }
                if (!normalizedKeyword.isEmpty() && !containsIgnoreCase(item.foodName(), normalizedKeyword)) {
                    continue;
                }
                matched.add(item);
            }

            matched.sort(Comparator.comparing(AdminImageItemDto::foodId));
            int total = matched.size();
            int from = (int) Math.min((long) (safePage - 1) * safeSize, total);
            int to = Math.min(from + safeSize, total);
            return AdminImagePageDto.of(List.copyOf(matched.subList(from, to)), total, safePage, safeSize);
        }
    }

    public AdminImageItemDto review(long foodId, String status) {
        String target = status == null ? "" : status.trim().toLowerCase(Locale.ROOT);
        if (!REVIEW_STATUSES.contains(target)) {
            throw ApiException.badRequest("status 只能是 approved 或 rejected");
        }

        synchronized (fileLock) {
            if (!Files.isRegularFile(manifestPath)) {
                throw ApiException.conflict(MISSING_HINT);
            }

            Manifest manifest = readManifest();
            for (CsvRecord record : manifest.dataRecords()) {
                Long currentId = parseFoodId(cell(record, manifest.columns(), COL_FOOD_ID));
                if (currentId != null && currentId.longValue() == foodId) {
                    setCell(record, manifest.columns().get(COL_REVIEW_STATUS), target);
                    writeManifest(manifest.records(), manifest.eol());
                    return toItem(foodId, record, manifest.columns());
                }
            }
            throw ApiException.notFound("图片清单中不存在该食物：" + foodId);
        }
    }

    // ------------------------------------------------------------------ 清单读取与写回

    private Manifest readManifest() {
        String text;
        try {
            text = Files.readString(manifestPath, StandardCharsets.UTF_8);
        } catch (IOException ex) {
            log.error("读取图片清单失败 path={}", manifestPath, ex);
            throw ApiException.internal("读取图片清单失败");
        }

        // Windows 下用 Excel/记事本保存的 UTF-8 常带 BOM，不剥掉会让第一列名变成 \ufefffood_id，
        // 表头匹配失败后整个审核接口都不可用
        if (!text.isEmpty() && text.charAt(0) == '\uFEFF') {
            text = text.substring(1);
        }
        // 保持原文件的换行风格，避免每次审核都把整份清单变成 CRLF/LF 的全文件 diff
        String eol = text.contains("\r\n") ? "\r\n" : "\n";

        List<CsvRecord> records = parseCsv(text);
        if (records.isEmpty()) {
            throw ApiException.internal("图片清单为空，缺少表头");
        }

        Map<String, Integer> columns = new HashMap<>();
        CsvRecord header = records.get(0);
        for (int i = 0; i < header.values().size(); i++) {
            columns.put(header.values().get(i).trim().toLowerCase(Locale.ROOT), i);
        }
        for (String required : REQUIRED_COLUMNS) {
            if (!columns.containsKey(required)) {
                throw ApiException.internal("图片清单表头缺少列：" + required);
            }
        }

        return new Manifest(records, records.subList(1, records.size()), columns, eol);
    }

    private void writeManifest(List<CsvRecord> records, String eol) {
        Path directory = manifestPath.getParent() == null ? Paths.get(".") : manifestPath.getParent();
        Path temp = null;
        try {
            temp = Files.createTempFile(directory, "food-image-manifest", ".tmp");
            Files.writeString(temp, formatCsv(records, eol), StandardCharsets.UTF_8);
            // 先写临时文件再替换：中途异常也不会留下半截清单
            Files.move(temp, manifestPath, StandardCopyOption.REPLACE_EXISTING);
        } catch (IOException ex) {
            log.error("写回图片清单失败 path={}", manifestPath, ex);
            if (temp != null) {
                try {
                    Files.deleteIfExists(temp);
                } catch (IOException ignored) {
                    // 临时文件清理失败不影响主流程错误
                }
            }
            throw ApiException.internal("保存图片清单失败");
        }
    }

    /**
     * 最小 RFC4180 解析：
     * - 引号只在字段起始位置才有包裹语义；
     * - 引号内 "" 表示一个双引号，逗号与换行都属于字段内容；
     * - 记录引号标记，写回时对原本带引号的字段继续加引号，其余字段仅在必要时加。
     */
    private static List<CsvRecord> parseCsv(String text) {
        List<CsvRecord> records = new ArrayList<>();
        List<String> values = new ArrayList<>();
        List<Boolean> quoted = new ArrayList<>();
        StringBuilder field = new StringBuilder();
        boolean inQuotes = false;
        boolean fieldQuoted = false;
        boolean fieldStarted = false;

        for (int i = 0; i < text.length(); i++) {
            char ch = text.charAt(i);

            if (inQuotes) {
                if (ch == '"') {
                    if (i + 1 < text.length() && text.charAt(i + 1) == '"') {
                        field.append('"');
                        i++;
                    } else {
                        inQuotes = false;
                    }
                } else {
                    field.append(ch);
                }
                continue;
            }

            if (ch == '"' && !fieldStarted) {
                inQuotes = true;
                fieldQuoted = true;
                fieldStarted = true;
                continue;
            }
            if (ch == ',') {
                values.add(field.toString());
                quoted.add(fieldQuoted);
                field.setLength(0);
                fieldQuoted = false;
                fieldStarted = false;
                continue;
            }
            if (ch == '\r' || ch == '\n') {
                if (ch == '\r' && i + 1 < text.length() && text.charAt(i + 1) == '\n') {
                    i++;
                }
                values.add(field.toString());
                quoted.add(fieldQuoted);
                // 跳过文件末尾的空行，避免写回后多出一行
                if (!(values.size() == 1 && values.get(0).isEmpty())) {
                    // 复制成可变列表，审核时需要就地替换 review_status
                    records.add(new CsvRecord(new ArrayList<>(values), new ArrayList<>(quoted)));
                }
                values.clear();
                quoted.clear();
                field.setLength(0);
                fieldQuoted = false;
                fieldStarted = false;
                continue;
            }
            field.append(ch);
            fieldStarted = true;
        }

        if (fieldStarted || field.length() > 0 || !values.isEmpty()) {
            values.add(field.toString());
            quoted.add(fieldQuoted);
            if (!(values.size() == 1 && values.get(0).isEmpty())) {
                records.add(new CsvRecord(new ArrayList<>(values), new ArrayList<>(quoted)));
            }
        }
        return records;
    }

    private static String formatCsv(List<CsvRecord> records, String eol) {
        StringBuilder out = new StringBuilder();
        for (CsvRecord record : records) {
            for (int i = 0; i < record.values().size(); i++) {
                if (i > 0) {
                    out.append(',');
                }
                String value = record.values().get(i);
                boolean quoted = i < record.quoted().size() && Boolean.TRUE.equals(record.quoted().get(i));
                if (quoted || needsQuotes(value)) {
                    out.append('"').append(value.replace("\"", "\"\"")).append('"');
                } else {
                    out.append(value);
                }
            }
            out.append(eol);
        }
        return out.toString();
    }

    private static boolean needsQuotes(String value) {
        if (value == null || value.isEmpty()) {
            return false;
        }
        return value.indexOf(',') >= 0 || value.indexOf('"') >= 0
                || value.indexOf('\r') >= 0 || value.indexOf('\n') >= 0
                || value.startsWith(" ") || value.endsWith(" ");
    }

    // ------------------------------------------------------------------ 记录映射

    private static AdminImageItemDto toItem(long foodId, CsvRecord record, Map<String, Integer> columns) {
        String localPath = cell(record, columns, COL_LOCAL_PATH);
        return new AdminImageItemDto(
                foodId,
                cell(record, columns, COL_FOOD_NAME),
                localPath,
                localPath,
                cell(record, columns, COL_SOURCE_NAME),
                cell(record, columns, COL_SOURCE_URL),
                cell(record, columns, COL_PHOTOGRAPHER),
                cell(record, columns, COL_LICENSE),
                cell(record, columns, COL_ATTRIBUTION),
                cell(record, columns, COL_DOWNLOAD_STATUS),
                cell(record, columns, COL_REVIEW_STATUS));
    }

    private static String cell(CsvRecord record, Map<String, Integer> columns, String column) {
        Integer index = columns.get(column);
        if (index == null || index >= record.values().size()) {
            return "";
        }
        String value = record.values().get(index);
        return value == null ? "" : value;
    }

    private static void setCell(CsvRecord record, int index, String value) {
        while (record.values().size() <= index) {
            record.values().add("");
        }
        while (record.quoted().size() < record.values().size()) {
            record.quoted().add(Boolean.FALSE);
        }
        record.values().set(index, value);
    }

    private static Long parseFoodId(String value) {
        try {
            return Long.valueOf(value.trim());
        } catch (NumberFormatException ex) {
            return null;
        }
    }

    private static boolean containsIgnoreCase(String value, String lowerCaseKeyword) {
        return value != null && value.toLowerCase(Locale.ROOT).contains(lowerCaseKeyword);
    }

    private static String normalizeFilterStatus(String status) {
        String normalized = status == null || status.isBlank()
                ? STATUS_PENDING
                : status.trim().toLowerCase(Locale.ROOT);
        if (!FILTER_STATUSES.contains(normalized)) {
            throw ApiException.badRequest("status 只能是 pending、approved、rejected 或 all");
        }
        return normalized;
    }

    /** 保留表头与原始行，写回时整表重写但只替换 review_status 单元格 */
    private record Manifest(List<CsvRecord> records, List<CsvRecord> dataRecords,
                            Map<String, Integer> columns, String eol) {
    }

    /** values/quoted 都是可变列表：审核时只改对应单元格，其余列原样输出 */
    private record CsvRecord(List<String> values, List<Boolean> quoted) {
    }
}