#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知识文档导入与索引维护。

优先复用 nutrient_knowledge：一条已核验的营养素科普就是一篇知识文档。
同时支持 values-python/data/knowledge/*.md，便于后续补充非数据库来源的资料。

导入、更新、删除都以 doc_id 为粒度：
- 重新导入同一 doc_id 时先删旧块再写新块，避免旧版本残留；
- --rebuild 会重建整个 collection，适合切换嵌入模型或维度后使用。
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass
from datetime import date
from typing import Any

from ...config import REPO_ROOT
from ...db import connect
from ..settings import RagSettings, load_rag
from .chunker import (
    KnowledgeDocument,
    chunk_documents,
    load_markdown_documents,
)
from .retriever import Retriever

logger = logging.getLogger(__name__)

_GROUP_LABELS = {
    "PROXIMATE": "常量营养素",
    "VITAMIN": "维生素",
    "MINERAL": "矿物质",
    "FATTY_ACID": "脂肪酸与胆固醇",
}


@dataclass(frozen=True)
class IndexStats:
    documents: int
    chunks: int
    database_documents: int
    file_documents: int
    rebuilt: bool


def load_database_documents() -> list[KnowledgeDocument]:
    connection = connect()
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT nk.nutrient_code,
                       ni.name,
                       ni.nutrient_group,
                       ni.unit,
                       ni.rich_rule_type,
                       ni.rich_threshold_percent,
                       ni.rich_threshold_per_100g,
                       ni.rule_note,
                       nk.role,
                       nk.source_name,
                       nk.source_url,
                       nk.verified_at
                FROM nutrient_knowledge nk
                JOIN nutrient_info ni ON ni.code = nk.nutrient_code
                ORDER BY ni.nutrient_group, ni.sort_order
                """
            )
            rows = cursor.fetchall()
    finally:
        connection.close()

    documents: list[KnowledgeDocument] = []
    for row in rows:
        role = (row.get("role") or "").strip()
        if not role:
            continue

        content = _nutrient_document_content(row)
        verified_at = row.get("verified_at")
        version = verified_at.isoformat() if isinstance(verified_at, date) else "1"
        documents.append(
            KnowledgeDocument(
                doc_id=f"nutrient:{row['nutrient_code']}",
                title=f"{row['name']}的营养作用",
                content=content,
                source=row.get("source_name") or "食物营养库",
                source_url=row.get("source_url") or None,
                version=version,
                review_status="approved" if verified_at else "pending",
                metadata={
                    "type": "nutrient",
                    "nutrient_code": row["nutrient_code"],
                    "nutrient_group": row.get("nutrient_group"),
                    "unit": row.get("unit"),
                },
            )
        )
    return documents


def load_file_documents(settings: RagSettings) -> list[KnowledgeDocument]:
    return load_markdown_documents(settings.knowledge_dir)


class KnowledgeIngestionService:
    def __init__(
        self,
        *,
        retriever: Retriever | None = None,
        settings: RagSettings | None = None,
    ) -> None:
        self.settings = settings or load_rag()
        self.retriever = retriever or Retriever(settings=self.settings)

    def reindex(self, *, rebuild: bool = True, include_files: bool = True) -> IndexStats:
        database_documents = load_database_documents()
        file_documents = load_file_documents(self.settings) if include_files else []
        documents = [*database_documents, *file_documents]
        chunks = chunk_documents(documents)

        if rebuild:
            self.retriever.recreate(chunks)
        else:
            for document in documents:
                self.retriever.delete_document(document.doc_id)
            self.retriever.index(chunks)

        logger.info(
            "知识索引完成：%d 篇文档，%d 个切块，rebuild=%s",
            len(documents),
            len(chunks),
            rebuild,
        )
        return IndexStats(
            documents=len(documents),
            chunks=len(chunks),
            database_documents=len(database_documents),
            file_documents=len(file_documents),
            rebuilt=rebuild,
        )

    def upsert_documents(self, documents: list[KnowledgeDocument]) -> int:
        if not documents:
            return 0
        chunks = chunk_documents(documents)
        for document in documents:
            self.retriever.delete_document(document.doc_id)
        return self.retriever.index(chunks)

    def delete_document(self, doc_id: str) -> None:
        self.retriever.delete_document(doc_id)

    def ensure_indexed(self) -> None:
        """首次检索时自动建索引；已有数据则直接复用。"""
        if not self.settings.auto_index:
            return
        try:
            if self.retriever.store.count() > 0:
                return
        except Exception as exc:
            logger.warning("读取向量库失败，尝试重建索引：%s", exc)
        self.reindex(rebuild=True)


def _nutrient_document_content(row: dict[str, Any]) -> str:
    lines = [str(row.get("role") or "").strip()]

    group = _GROUP_LABELS.get(row.get("nutrient_group"), row.get("nutrient_group"))
    unit = row.get("unit")
    if group or unit:
        lines.append(f"所属分组：{group or '未分组'}；计量单位：{unit or '未配置'}。")

    rule_note = (row.get("rule_note") or "").strip()
    if rule_note:
        lines.append(f"富含判定说明：{rule_note}")
    else:
        rule_type = row.get("rich_rule_type")
        if rule_type == "NRV_PERCENT" and row.get("rich_threshold_percent") is not None:
            lines.append(
                f"富含判定：达到 {row['rich_threshold_percent']}% NRV 视为富含。"
            )
        elif rule_type == "ABSOLUTE" and row.get("rich_threshold_per_100g") is not None:
            lines.append(
                f"富含判定：每 100g 达到 {row['rich_threshold_per_100g']}{unit} 视为富含。"
            )

    return "\n".join(line for line in lines if line)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="导入营养知识并写入向量库")
    parser.add_argument("--rebuild", action="store_true", default=True, help="重建整个索引（默认）")
    parser.add_argument("--no-rebuild", dest="rebuild", action="store_false", help="增量更新")
    parser.add_argument("--no-files", dest="include_files", action="store_false", help="只导入数据库知识")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    stats = KnowledgeIngestionService().reindex(
        rebuild=args.rebuild,
        include_files=args.include_files,
    )
    print(
        f"文档 {stats.documents} 篇（数据库 {stats.database_documents}，文件 "
        f"{stats.file_documents}），切块 {stats.chunks} 个，rebuild={stats.rebuilt}"
    )
    print(f"知识文档目录：{REPO_ROOT / 'values-python' / 'data' / 'knowledge'}")


if __name__ == "__main__":
    main()