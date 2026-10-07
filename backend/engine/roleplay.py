# -*- coding: utf-8 -*-
"""灵云文创 · Character Simulation（角色扮演模拟）
关键场景先让角色 agent 互相交锋（只出对话，符合各自性格），
再把对话实录交给写手融入正文。解决网文对话"念说明书"、角色没辨识度的问题。
"""
import json
from engine.llm import chat


def simulate_scene(scene: dict, canon: dict) -> str:
    """让角色扮演本场景的对话。scene: director 拆的场景 dict。返回对话实录文本。"""
    goal = scene.get("goal", "") or ""
    location = scene.get("location", "") or ""
    conflict = scene.get("conflict", "") or ""
    characters = scene.get("characters", []) or []
    if len(characters) < 2:
        return ""

    # 人物性格：从 canon / beat 里尽量带一点
    char_desc = ""
    protag = canon.get("protagonist") or ""
    villain = canon.get("villain") or ""
    char_lines = []
    if protag:
        char_lines.append(f"主角：{protag}")
    if villain:
        char_lines.append(f"反派：{villain[:80]}")
    if char_lines:
        char_desc = "\n".join(char_lines) + "\n"

    prompt = f"""你是网文编剧，负责"排演"一场戏。下面这场戏，你要模拟出场人物的对话，让人物用符合自己性格和处境的话交锋。

【场景目标】{goal}
【地点】{location}
【核心冲突】{conflict}
【出场人物】{json.dumps(characters, ensure_ascii=False)}

【人物设定参考】
{char_desc}
【人物性格铁律】
1. 每个人说话方式必须不一样：主角冷静带锋芒，反派阴狠，配角各有口头禅/小动作
2. 对话要有潜台词、打断、省略、话里有话，不要辩论赛式完整表达
3. 冲突要升级：铺垫 → 挑衅 → 拉扯 → 爆发，不要一上来就摊牌
4. 每句标注说话人，格式：人物名：台词
5. 8-20 轮对话，最后一句要停在转折或悬念上

直接输出对话实录，不要解释、不要旁白。"""
    try:
        text = chat(messages=[{"role": "user", "content": prompt}],
                    temperature=0.9, max_tokens=1200, fast=True)
        text = (text or "").strip()
        # 简单校验：必须有至少 4 行"人物："
        lines = [l for l in text.split("\n") if "：" in l or ":" in l]
        if len(lines) >= 4:
            return text
    except Exception:
        pass
    return ""


def roleplay_for_chapter(scenes: list, canon: dict, max_scenes: int = 2) -> str:
    """对一章里最适合演的场景做角色扮演。返回对话实录（可多场景拼接）。"""
    if not scenes:
        return ""
    # 选对话密集场景：有人物≥2 且有冲突的，最多 max_scenes 个
    candidates = [s for s in scenes
                  if (s.get("characters") or []) and len(s.get("characters", [])) >= 2
                  and s.get("conflict")]
    if not candidates:
        return ""
    parts = []
    for sc in candidates[:max_scenes]:
        dialog = simulate_scene(sc, canon)
        if dialog:
            parts.append(f"【场景{sc.get('scene_no', '?')}·{sc.get('goal', '')}】\n{dialog}")
    return "\n\n".join(parts)
