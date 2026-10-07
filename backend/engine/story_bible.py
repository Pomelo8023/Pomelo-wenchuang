# -*- coding: utf-8 -*-
"""灵云文创 · Story Bible 自动更新
每章 commit 后调一次 LLM，提取本章带来的新事实/关系变化/世界状态，
合并进 canon.json 的 story_bible 字段，并 upsert relationships 表。
"""
import json
from engine.llm import chat


def update_story_bible(conn, canon: dict, project_name: str, chapter: int, title: str, draft: str, pp: dict) -> dict:
    """返回 {"facts_added": N, "relations_added": N}。失败静默返回空。"""
    try:
        # 当前 bible 已有 facts，避免重复
        bible = canon.get("story_bible") or {}
        existing_facts = bible.get("facts", [])[-50:]  # 只看最近50条，控制 prompt
        existing_rel = []
        try:
            rows = conn.execute(
                "SELECT entity1_id, entity2_id, relation_type, strength FROM relationships ORDER BY last_chapter DESC LIMIT 20"
            ).fetchall()
            existing_rel = [f"{r['entity1_id']}-{r['entity2_id']}({r['relation_type']})" for r in rows]
        except Exception:
            pass

        # 本章摘要：前 600 字 + postprocess 提取的人物/事件
        excerpt = draft[:600]
        chars = [c.get("name", "") for c in (pp.get("characters") or []) if c.get("name")]

        prompt = f"""你是小说故事线管理员。第{chapter}章《{title}》刚写完，请提取本章带来的【新事实】和【关系变化】。

【本章开头】
{excerpt}

【本章出场人物】：{', '.join(chars) if chars else '无'}

【已有事实（不要重复）】：{'; '.join(existing_facts[-20:]) if existing_facts else '无'}
【已有关系（不要重复）】：{'; '.join(existing_rel) if existing_rel else '无'}

只输出 JSON：
{{
  "new_facts": ["新事实1（如：新地点/新物品/新设定）", "..."],
  "relations": [{{"e1":"人物A","e2":"人物B","type":"friend|enemy|family|lover|mentor","strength":-50到50整数}}],
  "world_note": "本章末世界状态一句话（可选）"
}}

没有新事实就返回空数组。直接输出 JSON。"""

        text = chat(messages=[{"role": "user", "content": prompt}], temperature=0.2, max_tokens=500, fast=True)
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        result = json.loads(text)

        facts = result.get("new_facts") or []
        rels = result.get("relations") or []
        world_note = (result.get("world_note") or "").strip()

        # 1. 合并进 canon.story_bible
        new_facts_list = existing_facts + [f"[第{chapter}章] {f}" for f in facts if f]
        bible["facts"] = new_facts_list[-100:]  # 最多留100条
        if world_note:
            bible["world_state"] = world_note
        canon["story_bible"] = bible

        # 2. upsert relationships 表
        n_rel = 0
        for r in rels:
            e1 = (r.get("e1") or "").strip()
            e2 = (r.get("e2") or "").strip()
            rtype = (r.get("type") or "").strip()
            strength = int(r.get("strength") or 0)
            if not e1 or not e2 or not rtype:
                continue
            # 已存在则更新 strength/last_chapter
            row = conn.execute(
                "SELECT id FROM relationships WHERE entity1_id=? AND entity2_id=?", (e1, e2)
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE relationships SET strength=?, relation_type=?, last_chapter=? WHERE id=?",
                    (strength, rtype, chapter, row["id"])
                )
            else:
                conn.execute(
                    "INSERT INTO relationships (entity1_id, entity2_id, relation_type, strength, first_chapter, last_chapter) VALUES (?,?,?,?,?,?)",
                    (e1, e2, rtype, strength, chapter, chapter)
                )
                n_rel += 1
        conn.commit()

        return {"facts_added": len(facts), "relations_added": n_rel}
    except Exception as e:
        return {"facts_added": 0, "relations_added": 0, "error": str(e)[:80]}
