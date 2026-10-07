# -*- coding: utf-8 -*-
"""灵云文创 · 摘要压缩器（compactor）
每写5章，把最老的几章摘要压成一句话，防止 context 越堆越长。
"""
from engine.llm import chat


def compact_old_summaries(conn, current_chapter: int, threshold: int = 30):
    """把 current_chapter - threshold 之前的长摘要压成一句短摘要。

    threshold=30：写第35章时，把第5章之前的摘要压短。
    """
    if current_chapter < 10:
        return  # 前10章不压

    rows = conn.execute("""
        SELECT chapter, title, summary FROM chapters
        WHERE chapter < ? AND length(summary) > 80
        ORDER BY chapter
        LIMIT 5
    """, (current_chapter - threshold,)).fetchall()

    if not rows:
        return

    for row in rows:
        try:
            new_summary = chat(
                messages=[{"role": "user", "content":
                    f"把下面这段章节摘要压成一句话（30字以内，保留关键剧情和伏笔）：\n\n{row['summary']}"}],
                temperature=0.2, max_tokens=100, fast=True,
            )
            conn.execute("UPDATE chapters SET summary=? WHERE chapter=?",
                         (new_summary.strip(), row["chapter"]))
        except Exception:
            continue
    conn.commit()
