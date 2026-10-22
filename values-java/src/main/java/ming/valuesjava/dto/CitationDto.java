package ming.valuesjava.dto;

/**
 * 回答引用。kind=food 表示营养库数值，kind=knowledge 表示 RAG 知识文档。
 * score 为向量召回相似度；食物数据引用固定为 1.0。
 */
public record CitationDto(
        String documentId,
        String title,
        String source,
        String url,
        String snippet,
        Double score,
        String kind,
        String reviewStatus,
        String version) {
}