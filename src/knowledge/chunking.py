"""Chunking de Markdown por secao, preservando o titulo da secao como metadado."""
from __future__ import annotations

import re

MAX_CHARS = 600


def _split_long(paragraph: str, limit: int) -> list[str]:
    parts, current = [], ""
    for sentence in re.split(r"(?<=[.!?;])\s+", paragraph):
        while len(sentence) > limit:  # sentenca gigante: corte duro
            if current:
                parts.append(current)
                current = ""
            parts.append(sentence[:limit])
            sentence = sentence[limit:]
        if current and len(current) + 1 + len(sentence) > limit:
            parts.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        parts.append(current)
    return parts


def chunk_markdown(body: str, max_chars: int = MAX_CHARS) -> list[dict]:
    """Retorna [{content, section, chunk_index}] sem chunks vazios; nenhum chunk atravessa o limite de secao."""
    sections: list[tuple[str, list[str]]] = [("(inicio)", [])]
    for block in re.split(r"\n\s*\n", body.replace("\r\n", "\n").strip()):
        block = block.strip()
        if not block:
            continue
        heading = re.match(r"^#{1,6}\s+(.+)$", block.split("\n", 1)[0])
        if heading:
            sections.append((heading.group(1).strip(), []))
            block = block.split("\n", 1)[1].strip() if "\n" in block else ""
        if block:
            sections[-1][1].append(re.sub(r"\s*\n\s*", " ", block))
    chunks: list[dict] = []
    for title, paragraphs in sections:
        current = ""
        for paragraph in (p for para in paragraphs for p in ([para] if len(para) <= max_chars else _split_long(para, max_chars))):
            if current and len(current) + 2 + len(paragraph) > max_chars:
                chunks.append({"content": current, "section": title})
                current = paragraph
            else:
                current = f"{current}\n\n{paragraph}".strip()
        if current:
            chunks.append({"content": current, "section": title})
    return [{**c, "chunk_index": i} for i, c in enumerate(chunks)]
