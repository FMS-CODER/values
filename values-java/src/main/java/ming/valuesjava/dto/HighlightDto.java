package ming.valuesjava.dto;

import java.math.BigDecimal;

/**
 * 营养亮点。
 * ruleLabel 由后端按阈值拼成可读文案（如「每 100g ≥30% NRV」），前端不重复实现规则拼接逻辑。
 */
public record HighlightDto(
        String code,
        String name,
        String unit,
        BigDecimal amount,
        BigDecimal nrvPercent,
        String ruleLabel,
        String ruleNote,
        String role,
        String sourceName,
        String sourceUrl,
        String verifiedAt) {
}