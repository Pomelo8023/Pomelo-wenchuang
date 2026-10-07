# -*- coding: utf-8 -*-
"""灵云文创 · 上下文打包（四层记忆：L1 beat / L2 近10章 / L3 本卷主线 / L4 canon + 关键词检索）"""
import sqlite3
import re
from database import crud


def search_relevant(conn: sqlite3.Connection, keyword: str, limit: int = 3) -> list:
    """FTS5 全文检索，回退 LIKE"""
    if not keyword or len(keyword) < 2:
        return []
    max_ch = conn.execute("SELECT MAX(chapter) m FROM chapters").fetchone()["m"] or 0
    # 先试 FTS5
    try:
        rows = conn.execute("""
            SELECT chapter, title, snippet(chapters_fts, 2, '【', '】', '...', 12) as snip
            FROM chapters_fts WHERE chapters_fts MATCH ? AND chapter < ?
            ORDER BY chapter DESC LIMIT ?
        """, (keyword, max_ch, limit)).fetchall()
        if rows:
            return [{"chapter": r["chapter"], "title": r["title"], "snippet": r["snip"]} for r in rows]
    except Exception:
        pass
    # 回退 LIKE
    rows = conn.execute("""
        SELECT chapter, title, content FROM chapters
        WHERE chapter < ? AND content LIKE ?
        ORDER BY chapter DESC LIMIT ?
    """, (max_ch, f"%{keyword}%", limit)).fetchall()
    results = []
    for r in rows:
        content = r["content"]
        idx = content.find(keyword)
        snippet = content[max(0, idx-50):idx+150] if idx >= 0 else content[:100]
        results.append({"chapter": r["chapter"], "title": r["title"], "snippet": snippet})
    return results


def build_task_brief(conn: sqlite3.Connection, chapter: int, total: int, beat: dict = None, proj_dir=None) -> str:
    meta = crud.get_meta(conn)
    chars = crud.list_characters(conn)
    active = crud.list_active_foreshadows(conn)

    # 题材规则（从canon.json读取，因为genre保存在canon里）
    from engine.genres import get_genre_rules
    genre = "都市重生智斗"
    if proj_dir:
        try:
            from engine.truth import TruthFile
            canon_data = TruthFile(proj_dir).get_canon()
            genre = canon_data.get("genre", "都市重生智斗")
        except Exception:
            pass
    if not genre or genre == "自动":
        genre = meta.get("genre", "都市重生智斗")
    genre_rules = get_genre_rules(genre)

    # L2: 分层摘要（最近1章全文 + 近5章完整摘要 + 6-15章压缩摘要 + 更早卷摘要）
    recent5 = conn.execute("""
        SELECT chapter, title, summary FROM chapters
        WHERE chapter < ? AND summary != ''
        ORDER BY chapter DESC LIMIT 5
    """, (chapter,)).fetchall()

    older = conn.execute("""
        SELECT chapter, title, summary FROM chapters
        WHERE chapter < ? AND summary != ''
        ORDER BY chapter DESC LIMIT 10 OFFSET 5
    """, (chapter,)).fetchall()

    # 上章结尾 500 字
    prev = conn.execute("SELECT content FROM chapters WHERE chapter=?", (chapter - 1,)).fetchone()
    tail = prev["content"][-500:] if prev else ""

    # 主角
    protagonist = next((c for c in chars if c["role_type"] == "protagonist"), None)

    # 推算本卷位置（每卷 30 章）
    volume_no = (chapter - 1) // 30 + 1
    volume_ch = (chapter - 1) % 30 + 1

    parts = []

    # ===== L4: Canon 顶层 =====
    parts.append(f"【书名】{meta.get('title') or '未命名'}\n第{chapter}章 / 共{total}章（第{volume_no}卷 · 本卷第{volume_ch}章）")

    # ===== 题材规则（强制遵守）=====
    if genre_rules:
        parts.append(genre_rules + "\n【题材铁律】严格按照上述题材写，不要混入其他题材元素（如历史古代不要写修仙/灵力/筑基）。")

    # ===== L3: 全书大纲（大框架）=====
    if proj_dir:
        from engine.truth import TruthFile
        canon = TruthFile(proj_dir).get_canon()
    else:
        canon = {}
    outline = canon.get("outline")
    if outline and isinstance(outline, dict) and outline.get("phases"):
        # 找当前阶段
        for p in outline["phases"]:
            rng = p.get("chapters", "")
            if "-" in rng:
                try:
                    start, end = rng.split("-")
                    if int(start) <= chapter <= int(end):
                        parts.append(f"【当前阶段：{p['name']}（{rng}）】{p.get('summary','')}")
                        if p.get("emotion_curve"):
                            parts.append(f"【情绪曲线】{p['emotion_curve']}")
                        break
                except Exception:
                    pass
        # 反派升级表
        villains = outline.get("villain_progression", [])
        for v in villains:
            rng = v.get("chapter", "")
            if "-" in rng:
                try:
                    start, end = rng.split("-")
                    if int(start) <= chapter <= int(end):
                        parts.append(f"【当前反派】{v.get('villain','')}（{v.get('power','')}）")
                        break
                except Exception:
                    pass
        # 事件级大纲（STORYWRITER）：找当前章节区间命中的核心事件
        events = outline.get("events", [])
        current_events = []
        for ev in events:
            rng = ev.get("chapter_range", "")
            if "-" in rng:
                try:
                    start, end = rng.split("-")
                    if int(start) <= chapter <= int(end):
                        current_events.append(ev)
                except Exception:
                    pass
        if current_events:
            lines = ["【本章核心事件（按此推进）】"]
            for ev in current_events[:3]:
                ev_type = ev.get("type", "主线")
                lines.append(f"  · [{ev_type}] {ev.get('title','')}：{ev.get('summary','')}")
            parts.append("\n".join(lines))

    # ===== L2: 分层摘要 =====
    # L2: 向量检索（语义记忆，受开关控制）
    vrag_on = bool((canon.get("engine_toggles") or {}).get("vector_rag"))
    if vrag_on and beat:
        try:
            from engine.vectorstore import search as vsearch
            pname = proj_dir.name if proj_dir else "default"
            related = vsearch(pname, beat.get("goal", ""), n_results=2)
            if related:
                lines = ["【语义检索到的相关章节】"]
                for r in related:
                    lines.append(f"  第{r['chapter']}章《{r['title']}》：{r['content'][:120]}")
                parts.append("\n".join(lines))
        except Exception:
            pass

    # 近5章完整摘要
    if recent5:
        lines = ["【近5章完整回顾】"]
        for r in reversed(list(recent5)):
            lines.append(f"  第{r['chapter']}章《{r['title'] or ''}》：{r['summary']}")
        parts.append("\n".join(lines))
    # 6-15章压缩摘要（每章一句话）
    if older:
        lines = ["【6-15章压缩回顾】"]
        for r in reversed(list(older)):
            s = r['summary'] or ''
            # 压缩到50字以内
            if len(s) > 50:
                s = s[:50] + '...'
            lines.append(f"  第{r['chapter']}章：{s}")
        parts.append("\n".join(lines))
    # 卷摘要（更早的内容）
    if proj_dir:
        from engine.truth import TruthFile
        canon_data = TruthFile(proj_dir).get_canon()
    else:
        canon_data = {}
    volume_summary = canon_data.get("volume_summary", {})
    current_vol = (chapter - 1) // 30 + 1
    if current_vol > 1 and str(current_vol - 1) in volume_summary:
        parts.append(f"【上一卷（第{current_vol-1}卷）摘要】{volume_summary[str(current_vol-1)]}")

    # Rolling State Block（游戏存档）
    state_block = canon_data.get("state_block", "")
    if state_block:
        parts.append(f"【当前状态（游戏存档）】\n{state_block}")

    # ===== 世界观（设定页）=====
    world_setting = canon_data.get("world_setting", "")
    if world_setting:
        parts.append(f"【世界观】{world_setting[:500]}")

    # ===== 时间线（最近事件）=====
    try:
        timeline_path = proj_dir / "story" / "state" / "timeline.json"
        if timeline_path.exists():
            import json as _json
            tl = _json.loads(timeline_path.read_text(encoding="utf-8"))
            if tl:
                lines = ["【时间线·最近5个事件】"]
                for ev in tl[-5:]:
                    lines.append(f"  第{ev.get('chapter','?')}章：{ev.get('summary','')[:60]}")
                parts.append("\n".join(lines))
    except Exception:
        pass

    # ===== 实际发生的事件（最近10章）=====
    try:
        ev_rows = conn.execute("SELECT chapter, summary FROM events WHERE chapter < ? ORDER BY chapter DESC LIMIT 10", (chapter,)).fetchall()
        if ev_rows:
            lines = ["【已发生事件·最近10条】"]
            for ev in ev_rows:
                lines.append(f"  第{ev['chapter']}章：{ev['summary'][:60]}")
            parts.append("\n".join(lines))
    except Exception:
        pass

    # 活跃伏笔（全列，最多 10 个）
    if active:
        lines = [f"【未回收伏笔（{len(active)}个，本章至少推进一个）】"]
        for f in active[:10]:
            lifecycle = f.get('lifecycle', 'near-term')
            lines.append(f"  [#{f['id']}] [{lifecycle}] 第{f['plant_chapter']}章埋：{f['plant_summary']}")
        parts.append("\n".join(lines))

    if tail:
        parts.append(f"【上章结尾（直接衔接，不要重复）】\n...{tail}")

    # ===== L1: 人物状态 =====
    char_lines = []
    if protagonist:
        char_lines.append(
            f"主角：{protagonist['name']}，"
            f"境界：{protagonist.get('realm') or '未定'}，"
            f"状态：{protagonist.get('state') or '未知'}，"
            f"性格：{protagonist.get('personality') or '未定'}"
        )
    others = [c for c in chars if c["role_type"] != "protagonist" and c["name"]]
    for c in others[:8]:  # 原来5个，加到8个
        char_lines.append(f"配角：{c['name']}（{c.get('state', '')}）")
    parts.append("【人物当前状态】\n" + "\n".join(char_lines))

    # 角色知识边界：主角只知道他亲眼看到的
    parts.append("""【角色知识边界·严格遵守】
- 主角不知道反派的计划，除非他亲眼看到或亲耳听到
- 主角不知道配角的秘密，除非配角告诉他
- 不要写"主角心想：反派一定在计划什么"——他不知道
- 读者知道但主角不知道的信息差，才是爽点""")

    # ===== 反 AI 味 + 网文节奏 =====
    parts.append("""【怎么写更顺】
反AI味：
- 不要每段写完"起因→经过→结果→感悟"，删掉感悟，留余味
- 不要用"缓缓/淡淡/微微/轻轻"，用具体动作替代
- 不要让所有人都"瞳孔微缩/心中一凛"，给每个角色专属微动作
- 对话带潜台词、打断、省略，不要辩论赛式完整表达
- 情绪不要贴标签，改写生理反应+微动作
- 有的段落只有一句话，有的十几句，制造疏密对比

网文节奏：
- 每章必须改变冲突/情绪/关系/知识中的至少一项，不能原地踏步
- 章末停在新问题或新压力上，不要把所有事讲完
- 开头300字必须抓人，不要先讲世界观
- 上章的钩子本章必须回应
- 字数2000-3000字
""")

    parts.append("【收在哪里】本章结束时留一个钩子（悬念/爽点/危机），让读者想看下一章。")

    # L5: 关键词检索相关历史片段（确定性 RAG，GROVE 式检索增强）
    if beat:
        search_terms = []
        for k in [beat.get("goal", ""), beat.get("conflict", ""), beat.get("info_gap", ""),
                  beat.get("hook_resolve_summary", ""), beat.get("hook_to_plant", "")]:
            search_terms.extend(re.findall(r'[\u4e00-\u9fa5]{2,4}', k or ""))
        # 出场人物名也作为检索词，找他们之前的故事
        for ch_name in beat.get("characters", [])[:3]:
            if isinstance(ch_name, str) and ch_name:
                search_terms.append(ch_name)
        seen = set()
        rel_lines = []
        for term in search_terms[:8]:
            if term in seen:
                continue
            seen.add(term)
            for hit in search_relevant(conn, term, limit=4):
                rel_lines.append(f"  第{hit['chapter']}章提到「{term}」：...{hit['snippet'][:150]}...")
        if rel_lines:
            parts.append("【相关历史片段（保持一致）】\n" + "\n".join(rel_lines[:10]))

    # ===== L6: 实体关联档案（超越向量 RAG：精确匹配，不是模糊向量）=====
    if beat:
        beat_text = beat.get("goal", "") + beat.get("conflict", "") + beat.get("hook", "")
        mentioned_names = re.findall(r'[\u4e00-\u9fa5]{2,3}(?=[说想道看走])', beat_text)
        if mentioned_names:
            detail_lines = ["【本章涉及人物完整档案（严格保持一致）】"]
            for name in list(dict.fromkeys(mentioned_names))[:5]:
                row = conn.execute(
                    "SELECT * FROM entities WHERE name LIKE ? OR aliases LIKE ?",
                    (f"%{name}%", f"%{name}%")).fetchone()
                if row:
                    r = dict(row)
                    detail_lines.append(
                        f"  · {r['name']}（{r.get('role_type','')}）："
                        f"境界/等级={r.get('realm','未定')}；"
                        f"性格={r.get('personality','未定')}；"
                        f"能力={r.get('abilities','未定')}；"
                        f"当前状态={r.get('state','未知')}；"
                        f"首次出场=第{r.get('first_chapter','?')}章"
                    )
            if len(detail_lines) > 1:
                parts.append("\n".join(detail_lines))

    return "\n\n".join(parts)
