"""知识摄入（RAG）：把本地文档/目录切块灌进长期记忆，对话时自动被回忆。

设计要点（与既有记忆系统无缝融合、不污染"懂你"画像）：
- 以 kind="knowledge"、importance=3 入库：
    · 不进画像（profile_summary 只取 preference/identity）；
    · 不被"遗忘"巩固清除（consolidate 只淘汰 importance<=2 的陈旧未用条目）；
    · 不会无条件常驻提示（recall 只对 importance>=4 无条件注入），仅在真正相关时被召回。
- facts.text 唯一约束天然去重，重复摄入幂等。
- 若 provider 支持 embed，则顺带向量化，语义检索/ANN 立即生效。
纯标准库，零第三方依赖。
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Iterator

# 视为文本的扩展名（白名单，避免读二进制）
TEXT_EXTS = {
    ".txt", ".md", ".markdown", ".rst", ".org", ".tex", ".log",
    ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".c", ".h",
    ".cpp", ".hpp", ".rb", ".php", ".sh", ".sql", ".html", ".css", ".vue",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".csv", ".tsv",
}


def chunk_text(text: str, max_chars: int = 800) -> list[str]:
    """按段落边界聚合成 ~max_chars 的块；超长段落硬切。保持语义单元尽量完整。"""
    text = (text or "").strip()
    if not text:
        return []
    paras = re.split(r"\n\s*\n", text)
    chunks: list[str] = []
    buf = ""
    for para in paras:
        para = para.strip()
        if not para:
            continue
        if len(para) > max_chars:                 # 单段过长 → 先冲掉缓冲，再硬切
            if buf:
                chunks.append(buf)
                buf = ""
            for i in range(0, len(para), max_chars):
                chunks.append(para[i:i + max_chars])
            continue
        if len(buf) + len(para) + 2 <= max_chars:
            buf = f"{buf}\n\n{para}" if buf else para
        else:
            if buf:
                chunks.append(buf)
            buf = para
    if buf:
        chunks.append(buf)
    return chunks


def iter_text_files(root: Path, max_file_kb: int = 1024) -> Iterator[Path]:
    """遍历目录下的文本文件（跳过隐藏目录、超大文件、非白名单扩展名）。"""
    for p in sorted(root.rglob("*")):
        if not p.is_file():
            continue
        if any(part.startswith(".") for part in p.relative_to(root).parts):
            continue                               # 跳过 .git/.venv 等隐藏目录/文件
        if p.suffix.lower() not in TEXT_EXTS:
            continue
        try:
            if p.stat().st_size > max_file_kb * 1024:
                continue
        except OSError:
            continue
        yield p


def ingest_path(memory, path: Path, *, tag: str = "", max_chars: int = 800,
                provider=None, max_file_kb: int = 1024) -> dict:
    """把文件或目录摄入长期记忆。返回 {files, chunks, embedded, skipped}。"""
    path = Path(path).expanduser()
    if path.is_file():
        base, files = path.parent, [path]
    elif path.is_dir():
        base, files = path, list(iter_text_files(path, max_file_kb))
    else:
        raise FileNotFoundError(f"路径不存在：{path}")

    n_files, n_chunks, skipped = 0, 0, 0
    for f in files:
        try:
            raw = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            skipped += 1
            continue
        chunks = chunk_text(raw, max_chars)
        if not chunks:
            continue
        try:
            rel = f.relative_to(base)
        except ValueError:
            rel = f.name
        source = f"ingest:{rel}"
        n = len(chunks)
        for idx, ck in enumerate(chunks):
            head = f"[{rel} · 第{idx + 1}/{n}块]\n" if n > 1 else f"[{rel}]\n"
            memory.add_fact(head + ck, kind="knowledge", importance=3,
                            tags=tag, source=source)
        n_files += 1
        n_chunks += n

    embedded = 0
    if provider is not None and n_chunks:
        try:
            embedded = memory.embed_backfill(provider, limit=max(256, n_chunks))
        except Exception:  # noqa: BLE001
            embedded = 0
    return {"files": n_files, "chunks": n_chunks, "embedded": embedded, "skipped": skipped}
