#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""知识文档清洗与切块。

切块的目标不是「切得越小越好」，而是保证每块能独立表达一个完整意思：
- 优先按段落切；
- 单段过长再按中文句末标点切；
- 相邻块保留一小段重叠，避免检索时刚好把答案切在边界上。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?；;\n])")
_WHITESPACE = re.compile(r"[ \t\u3000]+")


@dataclass(frozen=True)
class KnowledgeDocument:
    """一篇待入库的知识文档。"""

    doc_id: str
    title: str
    content: str
    source: str
    source_url: str | None = None
    version: str = "1"
    review_status: str = "approved"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Chunk:
    """文档切块后的最小检索单元。"""

    chunk_id: str
    doc_id: str
    title: str
    text: str
    source: str
    source_url: str | None
    version: str
    review_status: str
    chunk_index: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def embedding_text(self) -> str:
        """标题参与向量化：知识库文档很短，标题往往比正文更能表达主题。"""
        return f"{self.title}\n{self.text}"

    def to_payload(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "title": self.title,
            "text": self.text,
            "source": self.source,
            "url": self.source_url or "",
            "version": self.version,
            "review_status": self.review_status,
            "chunk_index": self.chunk_index,
            "metadata": self.metadata,
            "nutrient_code": self.metadata.get("nutrient_code") or "",
            "kind": "knowledge",
        }


def clean_text(text: str) -> str:
    lines = []
    for raw in (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = _WHITESPACE.sub(" ", raw).strip()
        lines.append(line)

    # 连续空行压缩成一个，既保留段落边界，又不让空白占用切块预算
    cleaned: list[str] = []
    for line in lines:
        if not line and cleaned and not cleaned[-1]:
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()


def chunk_document(
    document: KnowledgeDocument,
    *,
    max_chars: int = 500,
    overlap: int = 80,
) -> list[Chunk]:
    content = clean_text(document.content)
    if not content:
        return []

    if len(content) <= max_chars:
        return [_build_chunk(document, content, 0)]

    pieces: list[str] = []
    for paragraph in re.split(r"\n{2,}", content):
        paragraph = paragraph.strip()
        if not paragraph:
            continue
        if len(paragraph) <= max_chars:
            pieces.append(paragraph)
            continue
        pieces.extend(piece.strip() for piece in _SENTENCE_SPLIT.split(paragraph) if piece.strip())

    chunks: list[str] = []
    buffer = ""
    for piece in pieces:
        candidate = f"{buffer}\n{piece}" if buffer else piece
        if len(candidate) <= max_chars:
            buffer = candidate
            continue
        if buffer:
            chunks.append(buffer)
            tail = buffer[-overlap:] if overlap > 0 else ""
            buffer = f"{tail}\n{piece}".strip()
        else:
            # 单句超过上限：按上限硬切，保证每块都不超过预算且不会无限循环
            step = max_chars - overlap if 0 < overlap < max_chars else max_chars
            remaining = piece
            while len(remaining) > max_chars:
                chunks.append(remaining[:max_chars])
                remaining = remaining[step:]
            buffer = remaining
    if buffer:
        chunks.append(buffer)

    return [
        _build_chunk(document, text, index)
        for index, text in enumerate(chunk for chunk in chunks if chunk.strip())
    ]


def chunk_documents(
    documents: list[KnowledgeDocument],
    *,
    max_chars: int = 500,
    overlap: int = 80,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    for document in documents:
        chunks.extend(chunk_document(document, max_chars=max_chars, overlap=overlap))
    return chunks


def load_markdown_document(path: Path) -> KnowledgeDocument:
    """读取带简单 front matter 的 Markdown 文档。

    front matter 只支持少量标量字段；不引入 YAML 依赖，避免为了几个标题字段
    给运行环境增加一个解析器。没有 front matter 时，用一级标题作为 title。
    """
    raw = path.read_text(encoding="utf-8")
    metadata: dict[str, Any] = {}
    body = raw

    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) == 3:
            front, body = parts[1], parts[2]
            for line in front.splitlines():
                if ":" not in line:
                    continue
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()

    title = metadata.get("title") or ""
    if not title:
        for line in body.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break
    if not title:
        title = path.stem

    return KnowledgeDocument(
        doc_id=metadata.get("doc_id") or f"file:{path.stem}",
        title=title,
        content=body.strip(),
        source=metadata.get("source") or "本地知识文档",
        source_url=metadata.get("url") or None,
        version=metadata.get("version") or "1",
        review_status=metadata.get("review_status") or "approved",
        metadata={"file": path.name, **metadata},
    )


def load_markdown_documents(directory: Path) -> list[KnowledgeDocument]:
    if not directory.exists():
        return []
    return [load_markdown_document(path) for path in sorted(directory.glob("*.md"))]


def _build_chunk(document: KnowledgeDocument, text: str, index: int) -> Chunk:
    return Chunk(
        chunk_id=f"{document.doc_id}#{index}",
        doc_id=document.doc_id,
        title=document.title,
        text=text.strip(),
        source=document.source,
        source_url=document.source_url,
        version=document.version,
        review_status=document.review_status,
        chunk_index=index,
        metadata=dict(document.metadata),
    )