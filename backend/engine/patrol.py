# -*- coding: utf-8 -*-
"""灵云文创 · 跨章矛盾巡检（Patrol）
每 N 章自动回扫最近章节，找设定矛盾/人物 OOC/时间线错乱，输出问题列表。
只报告不自动改（怕改飞），由用户决定。
"""
import json
from engine.llm import chat


def patrol_recent(conn, up_to_chapter: int, lookback: int = 10) -> list:
    """取最近 lookback 章内容，LLM 找矛盾。返回问题字符串列表。"""
    rows = conn.execute(
        "SELECT chapter, title, content FROM chapters WHERE chapter <= ? ORDER BY chapter DESC LIMIT ?",
        (up_to_chapter, lookback)
    ).fetchall()
    if len(rows) < 2:
        return []
    rows = list(reversed(rows))

    excerpts = []
    for r in rows:
        # 每章取前 400 字，控制 token
        excerpts.append(f"第{r['chapter']}章《{r['title']}》：\n{(r['content'] or '')[:400]}")

    prompt = f"""你是小说逻辑审校。下面是最近{len(rows)}章的开头片段，请找跨章矛盾：

{chr(10).join(excerpts)}

只输出 JSON：{{"issues": ["问题1", "问题2"]}}，问题指：
1. 人物言行前后矛盾（性格突变、忽敌忽友无铺垫）
2. 时间线错乱（季节/日期/伤势恢复不合理）
3. 设定冲突（已死人物又出现、已毁法宝又拿出）
4. 信息不一致（同一人物两个名字/两种身份）

没有问题就返回空数组。直接输出 JSON，不要解释。"""
    try:
        text = chat(messages=[{"role": "user", "content": prompt}], temperature=0.2, max_tokens=400, fast=True)
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(text)
        issues = result.get("issues", [])
        return [str(i)[:80] for i in issues if i]
    except Exception:
        return []
