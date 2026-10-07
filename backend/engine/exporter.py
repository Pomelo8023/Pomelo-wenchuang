# -*- coding: utf-8 -*-
"""灵云文创 · 全书导出 TXT"""
from pathlib import Path


def export_txt(conn, proj_dir: str | Path, title: str) -> str:
    """从 chapters 表导出全书为 TXT，返回文件路径"""
    proj_dir = Path(proj_dir)
    out_dir = proj_dir / "导出"
    out_dir.mkdir(exist_ok=True)
    rows = conn.execute(
        "SELECT title, content FROM chapters ORDER BY chapter"
    ).fetchall()
    lines = [f"{title}\n\n"]
    for r in rows:
        lines.append(r["title"] or "")
        lines.append("")
        lines.append(r["content"] or "")
        lines.append("")
        lines.append("")
    safe_title = "".join(ch for ch in title if ch not in '\\/:*?"<>|').strip() or "novel"
    out_path = out_dir / f"{safe_title}.txt"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return str(out_path)
