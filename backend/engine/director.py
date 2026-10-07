# -*- coding: utf-8 -*-
"""灵云文创 · Director Agent（导演）"""
"""根据全局大纲，为每章生成具体 beat（节拍），含爽点工程学+题材特化"""
import json
from engine.llm import chat
from engine.genres import get_genre_rules


COOL_POINT_TYPES = ["装逼打脸", "扮猪吃虎", "越级反杀", "打脸权威", "反派翻车", "甜蜜超预期"]


def generate_outline(total: int, canon: dict) -> dict:
    """生成全书大纲（大框架）"""
    genre = canon.get("genre", "都市重生智斗")
    title = canon.get("title", "")
    prompt = f"""你是网文大纲规划师。书名：{title}，题材：{genre}，共{total}章。

请输出JSON格式的全书大纲：
{{
  "phases": [
    {{
      "name": "开局",
      "chapters": "1-{max(10, total//10)}",
      "summary": "主角穿越/重生，展现金手指，第一个小爽点",
      "main_conflict": "主角适应新世界，建立初步优势",
      "emotion_curve": "压抑3章→爽2章→压抑2章→大爽1章"
    }},
    {{
      "name": "发展",
      "chapters": "{max(10, total//10)+1}-{total//2}",
      "summary": "主角势力扩大，遇到更强对手，打脸升级",
      "main_conflict": "主角与中期反派的对抗",
      "emotion_curve": "压2爽3交替，每10章一个中高潮"
    }},
    {{
      "name": "高潮",
      "chapters": "{total//2+1}-{total*3//4}",
      "summary": "大反派现身，主角面临最大危机，逆袭翻盘",
      "main_conflict": "主角与最终BOSS的正面冲突",
      "emotion_curve": "大压抑5章→大爽3章→更大压抑5章→终极爽"
    }},
    {{
      "name": "结局",
      "chapters": "{total*3//4+1}-{total}",
      "summary": "最终决战，主角登顶，收尾伏笔",
      "main_conflict": "最终决战",
      "emotion_curve": "一路爽到结局，最后大高潮"
    }}
  ],
  "villain_progression": [
    {{"chapter": "1-{total//10}", "villain": "小恶霸", "power": "街头级"}},
    {{"chapter": "{total//10+1}-{total//4}", "villain": "帮派老大", "power": "地区级"}},
    {{"chapter": "{total//4+1}-{total//2}", "villain": "城市大佬", "power": "城市级"}},
    {{"chapter": "{total//2+1}-{total*3//4}", "villain": "省级巨头", "power": "省级"}},
    {{"chapter": "{total*3//4+1}-{total}", "villain": "最终BOSS", "power": "国家级"}}
  ],
  "cool_points": [
    {{"chapter": "1", "type": "开局杀", "desc": "第一章就打脸"}},
    {{"chapter": "10", "type": "小高潮", "desc": "第一次大爽"}},
    {{"chapter": "{total//4}", "type": "中高潮", "desc": "阶段胜利"}},
    {{"chapter": "{total//2}", "type": "大高潮", "desc": "翻盘"}},
    {{"chapter": "{total*3//4}", "type": "超大高潮", "desc": "逆袭"}},
    {{"chapter": "{total}", "type": "结局爽", "desc": "登顶"}}
  ],
  "events": [
    {{"no": 1, "chapter_range": "1-3", "type": "主线|支线|伏笔", "title": "事件名", "summary": "事件发生了什么，30字内", "characters": ["涉及人物"], "hook": "关联伏笔（无则null）"}},
    {{"no": 2, "chapter_range": "4-7", "type": "主线", "title": "事件名", "summary": "...", "characters": [], "hook": null}}
  ]
}}

要求 events：生成 {max(15, total//3)} 个核心事件，覆盖全书，事件之间有因果递进，伏笔事件分散埋设。只输出JSON，不要解释。"""
    raw = chat(messages=[{"role": "user", "content": prompt}], temperature=0.7, max_tokens=1000)
    try:
        result = json.loads(raw)
        # 确保phases至少有4个
        if "phases" not in result or len(result.get("phases", [])) < 4:
            result["phases"] = [
                {"name": "开局", "chapters": f"1-{total//4}", "summary": "主角登场，建立初步优势"},
                {"name": "发展", "chapters": f"{total//4+1}-{total//2}", "summary": "势力扩大，遇到更强对手"},
                {"name": "高潮", "chapters": f"{total//2+1}-{total*3//4}", "summary": "大反派现身，逆袭翻盘"},
                {"name": "结局", "chapters": f"{total*3//4+1}-{total}", "summary": "最终决战，主角登顶"},
            ]
        if "events" not in result or not result.get("events"):
            result["events"] = [
                {"no": i+1, "chapter_range": f"{i*5+1}-{min((i+1)*5, total)}", "type": "主线",
                 "title": f"主线事件{i+1}", "summary": "推进主线", "characters": [], "hook": None}
                for i in range(max(15, total // 3))
            ]
        return result
    except Exception:
        return {"phases": [
            {"name": "开局", "chapters": f"1-{total//4}", "summary": "主角登场，建立初步优势"},
            {"name": "发展", "chapters": f"{total//4+1}-{total//2}", "summary": "势力扩大，遇到更强对手"},
            {"name": "高潮", "chapters": f"{total//2+1}-{total*3//4}", "summary": "大反派现身，逆袭翻盘"},
            {"name": "结局", "chapters": f"{total*3//4+1}-{total}", "summary": "最终决战，主角登顶"},
        ], "events": [
            {"no": i+1, "chapter_range": f"{i*5+1}-{min((i+1)*5, total)}", "type": "主线",
             "title": f"主线事件{i+1}", "summary": "推进主线", "characters": [], "hook": None}
            for i in range(max(15, total // 3))
        ]}


def generate_chapter_beat(chapter: int, total: int, canon: dict, active_hooks: dict, emotional_arc: list, scenes_enabled: bool = True) -> dict:
    last_climax_ch = 0
    for c in emotional_arc:
        if c.get("climax"):
            last_climax_ch = c["chapter"]
    chapters_since_climax = chapter - last_climax_ch

    hooks_brief = []
    aging_hooks = []  # 埋了超过30章的老伏笔
    for k, v in list(active_hooks.items())[:8]:
        plant_ch = v.get("plant_chapter", 0)
        age = chapter - plant_ch
        hooks_brief.append({"id": k, "summary": v.get("summary", ""), "planted_ch": plant_ch, "age": age})
        if age > 30:
            aging_hooks.append({"id": k, "summary": v.get("summary", ""), "age": age})

    genre = canon.get("genre", "都市重生智斗")
    genre_rules = get_genre_rules(genre)

    # 题材特化规则
    genre_specific = ""
    if genre in ("历史古代", "历史脑洞", "种田", "年代", "抗战谍战"):
        genre_specific = """【历史题材铁律·绝对不能违反】
- 不要系统流！不要"叮！"的系统提示音！不要任务奖励！
- 金手指必须是：穿越者记忆/现代知识/医术/工匠技术/历史先知
- 不要修仙/灵力/筑基/金丹等修仙元素
- 要有具体的历史细节：物价、官制、服饰、饮食、礼仪
- 主角靠知识和智慧碾压，不靠超能力"""
    elif genre in ("都市重生智斗", "都市异能", "都市脑洞"):
        genre_specific = """【都市题材铁律】
- 可以有系统/重生/异能，但要有明确规则和代价
- 要有现代都市真实感：职场/商业/社会规则
- 不要修仙元素"""
    elif genre == "修仙":
        genre_specific = """【修仙题材铁律】
- 境界严格：练气→筑基→金丹→元婴→化神
- 机缘四步：传闻→探索→争夺→收获
- 黑暗森林法则，不要圣母"""

    aging_warning = ""
    if aging_hooks:
        aging_warning = f"""【⚠ 伏笔老化警告】以下伏笔埋了超过30章，读者已经快忘了，本章必须回收其中一个：
{json.dumps(aging_hooks, ensure_ascii=False)}"""

    # 黄金三章特化
    golden_rules = ""
    if chapter == 1:
        golden_rules = """【黄金第1章 铁律】
- 前300字必须出现钩子（悬念/生死危机/金手指三选一）
- 主角立刻陷入绝境，不要铺垫天气/环境
- 设定只放10%，剩下90%藏在后续剧情里
- 章末必须留强钩子"""
    elif chapter == 2:
        golden_rules = """【黄金第2章 铁律】
- 金手指必须发威，降维打击小反派
- 解释主角为什么能翻盘
- 不要回忆过去，不要大段设定科普"""
    elif chapter == 3:
        golden_rules = """【黄金第3章 铁律】
- 第一个小高潮，爽点兑现
- 解决一个小问题后立刻抛出更大的新冲突
- 让读者明确知道这本书要讲什么（核心目标）"""

    prompt = f"""你是顶级网文导演，精通爽点工程学。为第 {chapter}/{total} 章生成具体 beat。

【全局设定】
{json.dumps(canon, ensure_ascii=False, indent=2)[:1500]}

{genre_rules}

{genre_specific}

{golden_rules}

【待回收伏笔】（从中选一个回收，或 null）
{json.dumps(hooks_brief, ensure_ascii=False)}

{aging_warning}

【情绪历史】最近3章：{json.dumps(emotional_arc[-3:], ensure_ascii=False)}
距上次高潮：{chapters_since_climax} 章（>5章必须小高潮）

【爽点工程学】
1. 六种模式：装逼打脸/扮猪吃虎/越级反杀/打脸权威/反派翻车/甜蜜超预期
2. 结构 30%铺垫 → 40%兑现 → 30%微反转
3. 压扬比按题材定
4. 信息差：读者知道但反派不知道
5. 打脸四步：铺垫→挑衅→拉扯→爆发

【读者契约理论】（InkOS精华）
1. 开头建立了什么承诺（爽点/悬念/情感），后面每章都要兑现这个承诺
2. 每章至少推进2个轴：剧情/知识/关系/地位/危险/资源/自我认知——至少1主1辅
3. 后果必须来自角色选择，不能靠巧合/敌人降智/突然开挂
4. 事件发生日期 ≠ 主角发现日期——发现过程要演出来
5. 安静章节也要有不可逆的变化，不能水

【番茄节奏公式】
- 每3章必须一个小爽点（打脸/赚第一桶金/突破）
- 每10章必须一个大高潮（打败Boss/身份揭示/大反转）
- 不连续两章无冲突
- 章末钩子强度逐章递增

输出 JSON：
{{
  "goal": "本章核心目标",
  "characters": ["出场人物"],
  "conflict": "核心冲突",
  "emotion": "主情绪",
  "intensity": 1-10,
  "is_climax": true,
  "cool_point_type": "{COOL_POINT_TYPES[0]}",
  "info_gap": "读者知道但反派不知道的",
  "pressure_release": "压3扬7",
  "must_cover_nodes": ["节点1","节点2","节点3"],
  "forbidden_zones": ["禁写1","禁写2"],
  "hook_to_resolve": "伏笔id或null",
  "hook_resolve_summary": "怎么收的或null",
  "hook_to_plant": "新伏笔或null",
  "ending_hook": "章末钩子"
}}
直接输出 JSON。"""

    text = chat(messages=[{"role": "user", "content": prompt}], temperature=0.7, max_tokens=1000, fast=True)
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        beat = json.loads(text)
    except json.JSONDecodeError:
        beat = {"goal": "推进剧情", "characters": [], "conflict": "未知",
                "emotion": "平", "intensity": 5, "is_climax": False, "ending_hook": "..."}
    for k, v in [("cool_point_type", "反派翻车"), ("info_gap", ""), ("pressure_release", "压3扬7"),
                 ("must_cover_nodes", []), ("forbidden_zones", []),
                 ("hook_to_resolve", None), ("hook_resolve_summary", None), ("hook_to_plant", None)]:
        beat.setdefault(k, v)
    # 场景层（DOC：Detailed Outline Control，把一章拆成可执行场景）
    if scenes_enabled:
        try:
            beat["scenes"] = generate_scenes(beat)
        except Exception:
            beat["scenes"] = []
    else:
        beat["scenes"] = []
    return beat


def generate_scenes(beat: dict) -> list:
    """DOC 场景层：把一章 beat 拆成 3-5 个具体场景，每个场景有目标/地点/人物/冲突"""
    goal = beat.get("goal", "推进剧情")
    hook_resolve = beat.get("hook_resolve_summary") or ""
    hook_plant = beat.get("hook_to_plant") or ""
    characters = beat.get("characters", [])
    prompt = f"""你是网文分镜导演。把下面这一章的剧情拆成 3-5 个场景，每个场景都要能独立成段、推进剧情。

【本章目标】{goal}
【出场人物】{json.dumps(characters, ensure_ascii=False)}
【本章要回收的伏笔】{hook_resolve or "无"}
【本章要埋的新伏笔】{hook_plant or "无"}
【禁写内容】{json.dumps(beat.get("forbidden_zones", []), ensure_ascii=False)}

输出 JSON 数组：
[
  {{"scene_no": 1, "goal": "本场景要达成的目标", "location": "地点", "characters": ["出场人物"], "conflict": "场景冲突", "transition": "如何过渡到下一场景", "length": "300-500字"}}
]

要求：
1. 场景顺序符合起承转合，第1个场景必须开门见山
2. 最后一个场景必须停在章末钩子上
3. 每个场景长度 300-600 字
4. 直接输出 JSON 数组，不要解释。"""
    try:
        text = chat(messages=[{"role": "user", "content": prompt}], temperature=0.6, max_tokens=800, fast=True)
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        scenes = json.loads(text)
        if isinstance(scenes, list) and 2 <= len(scenes) <= 6:
            return scenes
    except Exception:
        pass
    # 兜底：单场景
    return [{"scene_no": 1, "goal": goal, "location": "", "characters": characters,
             "conflict": beat.get("conflict", ""), "transition": "", "length": "全文"}]
