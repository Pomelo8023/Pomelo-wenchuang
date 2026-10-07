# -*- coding: utf-8 -*-
"""灵云文创 · 确定性 Engine 主循环（V3 核心）"""
"""事实层确定，语义层自主：Engine + Route 派发 Worker"""
import time
from database import crud
from config import get_project_db, get_project_dir
from engine import context, writer, director
from engine.route import route
from engine.truth import TruthFile
from engine import compactor, postprocess
from engine.llm import chat
from engine.character_consistency import CharacterConsistency


def run_engine(project_name: str, total_chapters: int, on_event=None, stop_event=None, start_chapter: int = 1):
    """
    确定性 Engine 主循环：
    - 每轮从 Store 读事实
    - 按 Route 决策表派发 Worker
    - 崩溃恢复 = 读 store 续跑
    - stop_event: threading.Event，set() 后主循环在章间退出
    """
    def emit(evt):
        evt["ts"] = time.strftime("%H:%M:%S")
        if on_event:
            try: on_event(evt)
            except Exception: pass

    def stopped() -> bool:
        return stop_event is not None and stop_event.is_set()

    db_path = get_project_db(project_name)
    proj_dir = get_project_dir(project_name)
    truth = TruthFile(proj_dir)
    char_consistency = CharacterConsistency(str(proj_dir))

    crud.init_db(db_path)
    conn = crud.get_conn(db_path)

    progress = crud.get_progress(conn)
    # 强制更新total_chapters和words_per
    crud.update_progress(conn, total_chapters=total_chapters)

    start_ch = start_chapter  # 强制从指定章开始，不读progress
    print(f"[ENGINE] start_ch={start_ch}, total_chapters={total_chapters}")
    crud.update_progress(conn, status="running", current_step="start")
    emit({"type": "status", "msg": f"Engine 启动：{project_name}，目标 {total_chapters} 章"})

    # 加载 Canon
    canon = truth.get_canon()
    from engine.settings import get_toggles
    toggles = get_toggles(canon)
    if not canon:
        meta = crud.get_meta(conn)
        canon = {
            "title": meta.get("title", ""),
            "genre": meta.get("genre", "都市重生智斗"),
            "protagonist": meta.get("protagonist_name", ""),
            "world": meta.get("world_setting", ""),
            "outline": meta.get("outline", ""),
            "power_system": meta.get("power_system", ""),
            "gold_finger": meta.get("gold_finger", ""),
            "villain": meta.get("villain", ""),
        }
        truth.set_canon(canon)

    # 主循环：每章走一遍 Route
    try:
        for chapter in range(start_ch, total_chapters + 1):
            print(f"[ENGINE] 进入第{chapter}章循环")
            if stopped():
                crud.update_progress(conn, status="paused", current_step="stopped")
                emit({"type": "warning", "msg": f"收到停止信号，已在第{chapter}章前暂停"})
                break

            t0 = time.time()
            retry_count = 0

            # 每章重读 canon/开关（用户在设置页改开关后下一章立即生效）
            try:
                canon = truth.get_canon()
                toggles = get_toggles(canon)
            except Exception:
                pass

            # ===== 状态：为当前章构建 =====
            state = {
                "is_completed": False,
                "has_arc_plan": bool(truth.get_canon()),
                "has_current_draft": False,
                "is_reviewed": False,
                "review_passed": False,
                "retry_count": retry_count,
                "is_committed": False,
            }

            emit({"type": "step", "chapter": chapter, "msg": f"第{chapter}章 Engine 启动"})
            print(f"[ENGINE] 第{chapter}章启动, has_arc_plan={state['has_arc_plan']}, has_draft={state['has_current_draft']}")

            # 第一次启动时先生成全书大纲
            if chapter == 1 and not canon.get("outline"):
                emit({"type": "step", "chapter": chapter, "msg": "正在生成全书大纲（大框架）..."})
                outline = director.generate_outline(total_chapters, canon)
                canon["outline"] = outline
                truth.set_canon(canon)
                emit({"type": "step", "chapter": chapter, "msg": f"全书大纲已生成：{len(outline.get('phases',[]))}个阶段、{len(outline.get('events',[]))}个核心事件"})

            # ===== Route 决策循环 =====
            while not state["is_completed"] and not state["is_committed"]:
                action = route(state)
                action_cn = {
                    "plan_arc": "正在生成本章大纲...",
                    "write_chapter": "正在写入本章内容...",
                    "review_chapter": "正在审核本章...",
                    "fix_issues": "正在修复问题...",
                    "commit_chapter": "正在保存本章..."
                }.get(action, action)
                emit({"type": "step", "chapter": chapter, "msg": action_cn})
                print(f"[ENGINE] 第{chapter}章 action={action}, state={state}")

                if action == "plan_arc":
                    import time as _time
                    t0 = _time.time()
                    crud.update_progress(conn, current_chapter=chapter, current_step="director")
                    emit({"type": "step", "chapter": chapter, "msg": "正在读取当前活跃伏笔..."})
                    active_hooks = truth.get_active_hooks()
                    emit({"type": "step", "chapter": chapter, "msg": "正在生成情感曲线..."})
                    arc = truth.get_emotional_arc()
                    emit({"type": "step", "chapter": chapter, "msg": "正在生成本章大纲（beat）..."})
                    beat = director.generate_chapter_beat(chapter, total_chapters, canon, active_hooks, arc, scenes_enabled=toggles.get("scenes", True))
                    state["has_arc_plan"] = True
                    state["beat"] = beat
                    t1 = _time.time()
                    emit({"type": "step", "chapter": chapter, "msg": f"本章大纲生成完成！耗时{t1-t0:.1f}秒"})
                    scenes = beat.get("scenes") or []
                    if not toggles.get("scenes", True):
                        scenes = []
                    if scenes:
                        emit({"type": "step", "chapter": chapter, "msg": f"场景拆解完成：本章拆为 {len(scenes)} 个场景"})

                elif action == "write_chapter":
                    import time as _time
                    t0 = _time.time()
                    emit({"type": "step", "chapter": chapter, "msg": "正在构建写作上下文..."})
                    print(f"[ENGINE] 第{chapter}章 进入write_chapter")
                    crud.update_progress(conn, current_step="writer", retry_count=state["retry_count"])
                    brief = context.build_task_brief(conn, chapter, total_chapters, beat=state.get("beat", {}), proj_dir=proj_dir)
                    # RAG/事件追踪：从 brief 里统计命中情况
                    try:
                        if "【相关历史片段" in brief:
                            seg = brief.split("【相关历史片段", 1)[1].split("\n\n", 1)[0]
                            n_rag = seg.count("第") 
                            emit({"type": "step", "chapter": chapter, "msg": f"RAG检索：命中 {n_rag} 条相关历史片段"})
                        if "【本章核心事件" in brief:
                            seg = brief.split("【本章核心事件", 1)[1].split("\n\n", 1)[0]
                            n_ev = seg.count("·")
                            emit({"type": "step", "chapter": chapter, "msg": f"事件级大纲：本章命中 {n_ev} 个核心事件"})
                    except Exception:
                        pass
                    beat = state.get("beat", {})
                    brief += f"\n\n【本章写前合同】\n目标：{beat.get('goal','')}\n核心冲突：{beat.get('conflict','')}\n章末钩子：{beat.get('ending_hook','')}"
                    
                    # 注入人物一致性上下文
                    try:
                        emit({"type": "step", "chapter": chapter, "msg": "正在注入人物一致性上下文..."})
                        char_context = char_consistency.get_all_characters_context()
                        if char_context:
                            brief += f"\n\n【人物一致性·必须遵守】\n{char_context}"
                    except Exception:
                        pass
                    
                    # 注入用户反馈（从AI对话里保存的修改建议）
                    try:
                        import json as _json
                        canon_path = proj_dir / "story" / "state" / "canon.json"
                        if canon_path.exists():
                            canon = _json.loads(canon_path.read_text(encoding="utf-8"))
                            user_feedback = canon.get("user_feedback", "")
                            if user_feedback:
                                brief += f"\n\n【用户最新反馈·必须参考】\n{user_feedback}"
                    except Exception:
                        pass

                    # 角色扮演排演（Character Simulation）：对话密集场景先演后写
                    roleplay_text = ""
                    if toggles.get("roleplay", True):
                        try:
                            emit({"type": "step", "chapter": chapter, "msg": "正在排演本章对话（角色扮演）..."})
                            from engine.roleplay import roleplay_for_chapter
                            roleplay_text = roleplay_for_chapter(state.get("beat", {}).get("scenes", []), canon)
                            if roleplay_text:
                                brief += f"\n\n【角色对话实录】\n{roleplay_text}"
                                import re as _re
                                n_scenes = len(_re.findall(r"【场景\d+", roleplay_text))
                                n_lines = sum(1 for l in roleplay_text.split("\n") if "：" in l or ":" in l)
                                emit({"type": "step", "chapter": chapter, "msg": f"角色扮演排演完成：{n_scenes} 场对话、共 {n_lines} 轮"})
                        except Exception:
                            pass
                    
                    draft = ""
                    write_ok = False
                    for attempt in range(3):
                        try:
                            char_count = [0]
                            def _on_delta(d):
                                if stopped():
                                    raise InterruptedError("用户暂停")
                                char_count[0] += len(d)
                                if char_count[0] % 200 < 10:
                                    emit({"type": "writing", "chapter": chapter, "chars": char_count[0]})
                            draft = writer.write_chapter(brief, on_delta=_on_delta, words_per=canon.get("words_per", 2200), words_min=canon.get("words_min", ""), words_max=canon.get("words_max", ""), chapter=chapter, stop_check=stopped, scenes=state.get("beat", {}).get("scenes"), roleplay_text=roleplay_text)
                            write_ok = True
                            break
                        except InterruptedError:
                            raise
                        except Exception as e:
                            emit({"type": "error", "chapter": chapter, "msg": f"写作失败：{str(e)[:100]}"})
                            import traceback
                            traceback.print_exc()
                    if not write_ok:
                        emit({"type": "error", "chapter": chapter, "msg": "写作3次均失败，跳过本章"})
                        state["is_committed"] = True
                        continue
                    
                    state["has_current_draft"] = True
                    state["draft"] = draft
                    print(f"[ENGINE] 第{chapter}章 write_chapter完成, draft长度={len(draft)}")

                elif action == "review_chapter":
                    state["is_reviewed"] = True
                    state["review_passed"] = True

                elif action == "wait_for_arbiter":
                    emit({"type": "warning", "chapter": chapter, "msg": "审查2次未通过，跳过本章"})
                    state["is_committed"] = True

                elif action == "commit_chapter":
                    crud.update_progress(conn, current_step="postprocess")
                    
                    # 字数范围解析（与 writer.py 一致：未设时取 words_per 的 ±10%）
                    def _to_int(v, default=0):
                        try:
                            return int(v) if v not in ("", None) else default
                        except (ValueError, TypeError):
                            return default
                    words_per = _to_int(canon.get("words_per"), 2200)
                    max_words = _to_int(canon.get("words_max"), int(words_per * 1.1))
                    min_words = _to_int(canon.get("words_min"), int(words_per * 0.9))

                    # 字数超标：专用精简 prompt（temperature 低，果断删）
                    if len(state["draft"]) > max_words:
                        emit({"type": "processing", "chapter": chapter, "msg": f"字数超标({len(state['draft'])}字)，正在精简到{min_words}-{max_words}..."})
                        trim_prompt = f"""以下是小说第{chapter}章的内容，现在有{len(state['draft'])}字，超过了{max_words}字！

请精简内容！目标字数 {max_words} 字！
【硬约束】最终字数必须落在 {min_words} ~ {max_words} 之间，不能少于 {min_words}，不能多于 {max_words}。

【精简要求】
1. 保留核心剧情和关键对话！
2. 删除冗余描写和废话！
3. 保持原来的风格、人物性格！
4. 不要加新内容！
5. 直接输出精简后的完整章节！

【章节内容】
{state['draft']}"""
                        state["draft"] = chat(
                            messages=[
                                {"role": "system", "content": "你是网文编辑，精简章节内容！删除冗余描写！保留核心剧情！"},
                                {"role": "user", "content": trim_prompt}
                            ],
                            temperature=0.3,
                            max_tokens=6000,
                        )
                        emit({"type": "processing", "chapter": chapter, "msg": f"精简完成，共{len(state['draft'])}字（目标{min_words}-{max_words}）"})

                    # 字数不足：专用扩写 prompt（temperature 高，补得生动）
                    elif len(state["draft"]) < min_words:
                        emit({"type": "processing", "chapter": chapter, "msg": f"字数不足({len(state['draft'])}字 < {min_words}字)，正在扩写到{min_words}-{max_words}..."})
                        expand_prompt = f"""以下是小说第{chapter}章的内容，现在只有{len(state['draft'])}字，低于{min_words}字。

请在原文基础上扩写！目标字数 {min_words} 字！
【硬约束】最终字数必须落在 {min_words} ~ {max_words} 之间，不能超过 {max_words}，不能少于 {min_words}。

【扩写要求】
1. 不改变已有剧情走向，不新增人物，不反转结局！
2. 在现有场景里加动作细节、环境描写、人物心理活动、对话延展！
3. 把写得太简略的段落展开！
4. 保持原来的风格和人物口吻！
5. 直接输出扩写后的完整章节！

【章节内容】
{state['draft']}"""
                        state["draft"] = chat(
                            messages=[
                                {"role": "system", "content": "你是网文编辑，在不改变剧情的前提下扩写章节！把简略段落写细！"},
                                {"role": "user", "content": expand_prompt}
                            ],
                            temperature=0.5,
                            max_tokens=6000,
                        )
                        emit({"type": "processing", "chapter": chapter, "msg": f"扩写完成，共{len(state['draft'])}字（目标{min_words}-{max_words}）"})
                    
                    # 检查是否暂停
                    if stopped():
                        raise InterruptedError("用户暂停")
                    
                    brief = context.build_task_brief(conn, chapter, total_chapters, beat=state.get("beat", {}), proj_dir=proj_dir)
                    # 字数范围（与上面扩写/精简口径一致）
                    words_min_int = min_words
                    words_max_int = max_words
                    try:
                        emit({"type": "step", "chapter": chapter, "msg": "正在进行后处理（审稿+提取+审计+标题）..."})
                        pp = postprocess.postprocess_chapter(state["draft"], brief, state.get("beat", {}), words_min_int, words_max_int, stop_check=stopped)
                    except Exception as e:
                        emit({"type": "warning", "chapter": chapter, "msg": f"后处理失败: {e}"})
                        pp = {"title": f"第{chapter}章", "characters": [], "events": [], "new_foreshadows": [], "overall_score": 5}
                    title = (pp.get("title") or f"第{chapter}章").strip().strip('"').strip("'")
                    data = {"characters": pp.get("characters", []), "events": pp.get("events", []), "new_foreshadows": pp.get("new_foreshadows", [])}
                    score = pp.get("overall_score", 5)
                    scores = pp.get("scores", {})
                    quant = pp.get("quantitative", {})
                    emit({"type": "step", "chapter": chapter, "msg": f"后处理完成！审计分 {score}/10！"})
                    
                    # 错误分级处理
                    # Critical：影响后续情节的重大逻辑断裂→标记+暂停
                    # High：人物性格突变、关键设定被违反→自动重写
                    # Medium：时间线混乱、次要细节错误→标记警告
                    # Low：用词问题→自动修正
                    critical_issues = pp.get("critical", [])
                    has_critical = any("矛盾" in i or "题材一致性低" in i for i in critical_issues)
                    has_high = any(
                        "高频词" in i or "AI味" in i or
                        "设定模糊" in i or "开篇" in i or
                        "对话过少" in i or "字数" in i or
                        "未覆盖必须节点" in i or "出现禁写内容" in i
                        for i in critical_issues
                    )
                    
                    # 核心维度验收门：核心维度<7必须重写，最多重试2次
                    core_dims = ["satisfaction", "pacing", "hook_strength", "characterization", 
                                "conflict_escalation", "ai_tone", "consistency", "show_dont_tell", "genre_consistency",
                                "emotional_investment", "structure_completeness", "dialogue_distinctiveness"]
                    retry_audit = 0
                    genre_score = scores.get("genre_consistency", 10)
                    
                    while retry_audit < 2:
                        # 检查核心维度
                        low_core = [k for k in core_dims if isinstance(scores.get(k), (int, float)) and scores[k] < 7]
                        # 检查量化问题
                        quant_issues = quant.get("issues", [])
                        
                        if not low_core and not has_critical and not has_high and not quant_issues:
                            break
                        
                        issues_list = []
                        if low_core:
                            issues_list.append(f"核心维度低：{', '.join(low_core)}")
                        if has_critical:
                            issues_list.append("重大逻辑矛盾")
                        if quant_issues:
                            issues_list.extend(quant_issues[:3])
                        
                        issues_str = "; ".join(issues_list)
                        emit({"type": "step", "chapter": chapter, "msg": f"核心维度未过（{score}/10），修正：{issues_str}"})
                        
                        try:
                            state["draft"] = writer.rewrite_chapter(state["draft"], issues_str)
                        except Exception as e:
                            emit({"type": "warning", "chapter": chapter, "msg": f"重写失败: {e}"})
                            break
                        
                        brief = context.build_task_brief(conn, chapter, total_chapters, beat=state.get("beat", {}), proj_dir=proj_dir)
                        try:
                            pp = postprocess.postprocess_chapter(state["draft"], brief, state.get("beat", {}), words_min_int, words_max_int)
                        except Exception as e:
                            emit({"type": "warning", "chapter": chapter, "msg": f"二次后处理失败: {e}"})
                            break
                        
                        score = pp.get("overall_score", 5)
                        scores = pp.get("scores", {})
                        quant = pp.get("quantitative", {})
                        genre_score = scores.get("genre_consistency", 10)
                        critical_issues = pp.get("critical", [])
                        has_critical = any("矛盾" in i or "题材一致性低" in i for i in critical_issues)
                        has_high = any(
                            "高频词" in i or "AI味" in i or
                            "设定模糊" in i or "开篇" in i or
                            "对话过少" in i or "字数" in i or
                            "未覆盖必须节点" in i or "出现禁写内容" in i
                            for i in critical_issues
                        )
                        retry_audit += 1
                        emit({"type": "step", "chapter": chapter, "msg": f"修正后审计分 {score}/10（第{retry_audit}次）"})

                    # ===== CRITICS：多批评者深审（评分通过后仍要过评审，最多再重写1次）=====
                    if toggles.get("critics", True):
                        try:
                            emit({"type": "step", "chapter": chapter, "msg": "正在多批评者深审（读者/编辑/逻辑三视角）..."})
                            from engine.critics import collective_review
                            c = collective_review(state["draft"], state.get("beat", {}), brief)
                            c_top = c.get("top_issues") or []
                            if c.get("verdict") == "revise" and c_top and retry_audit < 2:
                                c_issues = "; ".join(c_top[:2])
                                emit({"type": "step", "chapter": chapter, "msg": f"多批评者建议重写：{c_issues}"})
                                state["draft"] = writer.rewrite_chapter(state["draft"], c_issues)
                                retry_audit += 1
                                brief = context.build_task_brief(conn, chapter, total_chapters, beat=state.get("beat", {}), proj_dir=proj_dir)
                                pp = postprocess.postprocess_chapter(state["draft"], brief, state.get("beat", {}), words_min_int, words_max_int)
                                title = (pp.get("title") or title).strip().strip('"').strip("'")
                                data = {"characters": pp.get("characters", []), "events": pp.get("events", []), "new_foreshadows": pp.get("new_foreshadows", [])}
                                score = pp.get("overall_score", score)
                                scores = pp.get("scores", scores)
                                quant = pp.get("quantitative", quant)
                                emit({"type": "step", "chapter": chapter, "msg": f"批评者重写后审计分 {score}/10"})
                            elif c.get("verdict") == "revise":
                                emit({"type": "warning", "chapter": chapter, "msg": f"多批评者仍建议重写但次数已用尽，接受本章：{'; '.join((c_top or [])[:2]) or '（无具体理由）'}"})
                            else:
                                n_reader = len(c.get("reader_issues") or [])
                                n_editor = len(c.get("editor_issues") or [])
                                n_logic = len(c.get("logic_issues") or [])
                                if n_reader or n_editor or n_logic:
                                    emit({"type": "step", "chapter": chapter, "msg": f"多批评者评审通过（读者{n_reader}/编辑{n_editor}/逻辑{n_logic}视角无硬伤）"})
                                else:
                                    emit({"type": "step", "chapter": chapter, "msg": "多批评者评审通过（三视角无异议）"})
                        except Exception as e:
                            emit({"type": "warning", "chapter": chapter, "msg": f"多批评者评审失败: {e}"})
                    
                    if pp.get("critical"):
                        emit({"type": "warning", "chapter": chapter, "msg": f"警告：{'; '.join(pp['critical'][:3])}"})
                    if pp.get("next_chapter_hint"):
                        truth.add_reflection(chapter, {"next_chapter_hint": pp["next_chapter_hint"]})

                    # ===== 提交：DB 主记录先写，失败则回滚章节 =====
                    try:
                        crud.save_chapter(conn, chapter, title, state["draft"], summary="", commit_json=str(data))
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        emit({"type": "error", "chapter": chapter, "msg": f"保存失败: {str(e)[:200]}"})
                        raise

                    # ===== 伏笔：新埋入库 + 本章回收标记（失败则删章节回滚）=====
                    rollback_chapter = False
                    try:
                        # 强制落地导演悬念规划（即使后处理漏了）
                        try:
                            b = state.get("beat", {})
                            plant = (b.get("hook_to_plant") or "").strip()
                            if plant:
                                existing_new = pp.get("new_foreshadows", []) or []
                                already = [fs.get("summary", "") for fs in existing_new if isinstance(fs, dict)]
                                # 与已有伏笔判重（前10字互相包含视为同一条），避免重复入库
                                dup = any((plant[:10] in s) or (s[:10] in plant) for s in already if s)
                                if not dup:
                                    existing_new.append({"summary": plant, "type": "悬念", "strength": "medium"})
                                    pp["new_foreshadows"] = existing_new
                            resolve = (b.get("hook_resolve_summary") or "").strip()
                            if resolve:
                                existing_res = pp.get("resolved_foreshadows", []) or []
                                already_r = [s for s in existing_res if isinstance(s, str)]
                                dup_r = any((resolve[:10] in s) or (s[:10] in resolve) for s in already_r if s)
                                if not dup_r:
                                    existing_res.append(resolve)
                                    pp["resolved_foreshadows"] = existing_res
                        except Exception:
                            pass

                        def _overlap(a: str, b: str) -> bool:
                            a, b = a or "", b or ""
                            if not a or not b:
                                return False
                            grams_a = {a[i:i+3] for i in range(len(a)-2)}
                            return any(g in b for g in grams_a)

                        n_new = 0
                        n_resolved = 0
                        for fs in pp.get("new_foreshadows", []):
                            summary = (fs.get("summary") or "").strip()
                            if not summary:
                                continue
                            n_new += 1
                            crud.add_foreshadow(conn, {
                                "plant_chapter": chapter, "plant_summary": summary,
                                "type": fs.get("type", "悬念"),
                                "strength": fs.get("strength", "medium"),
                            })
                            hid = f"hook_{chapter}_{abs(hash(summary)) % 100000}"
                            truth.add_hook(hid, {
                                "plant_chapter": chapter, "summary": summary,
                                "type": fs.get("type", "悬念"),
                            })

                        resolved_list = pp.get("resolved_foreshadows", []) or []
                        if resolved_list:
                            active_rows = crud.list_active_foreshadows(conn)
                            for r_summary in resolved_list:
                                r_summary = (r_summary or "").strip()
                                if not r_summary:
                                    continue
                                matched = None
                                for row in active_rows:
                                    if _overlap(row["plant_summary"], r_summary):
                                        matched = row
                                        break
                                if matched:
                                    crud.resolve_foreshadow(conn, matched["id"], chapter, r_summary)
                                    n_resolved += 1
                                for hid, h in truth.get_active_hooks().items():
                                    if _overlap(h.get("summary", ""), r_summary):
                                        truth.resolve_hook(hid, chapter, r_summary)
                                        n_resolved += 1
                                        break
                        if n_new or n_resolved:
                            emit({"type": "step", "chapter": chapter, "msg": f"伏笔落地：新埋 {n_new} 条、回收 {n_resolved} 条"})
                    except Exception as e:
                        emit({"type": "warning", "chapter": chapter, "msg": f"伏笔入库失败，回滚章节: {e}"})
                        rollback_chapter = True

                    # ===== 人物入库（失败则回滚章节）=====
                    if not rollback_chapter:
                        try:
                            for c in pp.get("characters", []):
                                name = (c.get("name") or "").strip()
                                if not name:
                                    continue
                                cid = "char_" + name
                                existing = crud.get_character(conn, cid) or {}
                                crud.upsert_character(conn, {
                                    "id": cid,
                                    "name": name,
                                    "aliases": existing.get("aliases", "[]"),
                                    "role_type": existing.get("role_type", "support"),
                                    "realm": existing.get("realm", ""),
                                    "personality": existing.get("personality", ""),
                                    "abilities": existing.get("abilities", "[]"),
                                    "state": c.get("state_change") or existing.get("state", ""),
                                    "first_chapter": existing.get("first_chapter", chapter),
                                    "last_chapter": chapter,
                                    "notes": existing.get("notes", ""),
                                    "archetype": c.get("archetype") or existing.get("archetype", "npc"),
                                })
                        except Exception as e:
                            emit({"type": "warning", "chapter": chapter, "msg": f"人物入库失败，回滚章节: {e}"})
                            rollback_chapter = True

                    # 回滚：删掉刚写的章节记录，避免孤儿数据
                    if rollback_chapter:
                        conn.execute("DELETE FROM chapters WHERE chapter=?", (chapter,))
                        conn.commit()
                        raise RuntimeError(f"第{chapter}章提交失败，已回滚")

                    # DB 全部成功后才写文件
                    (proj_dir / "正文" / f"第{chapter:04d}章 {title}.md").write_text(f"# {title}\n\n{state['draft']}", encoding="utf-8")

                    # 更新人物一致性系统（JSON 文件，不影响 DB 一致性）
                    try:
                        char_consistency.update_characters(chapter, pp.get("characters", []))
                        char_consistency.update_relations(chapter, pp.get("events", []))
                        char_consistency.update_timeline(chapter, pp.get("events", []))
                    except Exception as e:
                        emit({"type": "warning", "chapter": chapter, "msg": f"人物一致性更新失败: {e}"})

                    # 写事件到数据库
                    try:
                        for ev in (pp.get("events") or []):
                            crud.add_event(conn, chapter, ev.get("type", "unknown"), ev.get("summary", ""), 5)
                    except Exception as e:
                        emit({"type": "warning", "chapter": chapter, "msg": f"事件入库失败: {e}"})

                    # 写人物状态变化表
                    if toggles.get("state_changes", True):
                        try:
                            n_sc = 0
                            for c in pp.get("characters", []):
                                sc = (c.get("state_change") or "").strip()
                                name = (c.get("name") or "").strip()
                                if sc and name:
                                    conn.execute(
                                        "INSERT INTO state_changes (entity_id, chapter, change_type, new_value) VALUES (?,?,?,?)",
                                        (f"char_{name}", chapter, "state", sc[:200]))
                                    n_sc += 1
                            conn.commit()
                            if n_sc:
                                emit({"type": "step", "chapter": chapter, "msg": f"人物状态记录：{n_sc} 条变化已入库"})
                        except Exception as e:
                            emit({"type": "warning", "chapter": chapter, "msg": f"人物状态记录失败: {str(e)[:80]}"})

                    # Story Bible 自动更新：提取本章新事实+关系变化，写回 canon 和 relationships 表
                    try:
                        from engine.story_bible import update_story_bible
                        sb = update_story_bible(conn, canon, project_name, chapter, title, state["draft"], pp)
                        if sb.get("facts_added") or sb.get("relations_added"):
                            truth.set_canon(canon)
                            emit({"type": "step", "chapter": chapter, "msg": f"故事圣经更新：新事实 {sb.get('facts_added',0)} 条、关系 {sb.get('relations_added',0)} 条"})
                        if sb.get("error"):
                            emit({"type": "warning", "chapter": chapter, "msg": f"故事圣经更新异常: {sb['error']}"})
                    except Exception as e:
                        emit({"type": "warning", "chapter": chapter, "msg": f"故事圣经更新失败: {str(e)[:80]}"})

                    # 写入向量索引（语义记忆）
                    if toggles.get("vector_rag", False):
                        try:
                            from engine.vectorstore import add_chapter
                            add_chapter(project_name, chapter, title, state["draft"])
                            emit({"type": "step", "chapter": chapter, "msg": "本章已入向量索引（语义记忆）"})
                        except Exception as e:
                            emit({"type": "warning", "chapter": chapter, "msg": f"向量索引写入失败: {str(e)[:80]}"})
                    
                    latency = int((time.time() - t0) * 1000)
                    crud.update_progress(conn, current_chapter=chapter, current_step="done")
                    # 估算token用量（中文大概1.5个字一个token）
                    input_tokens = int(len(brief) / 1.5)
                    output_tokens = int(len(state['draft']) / 1.5)
                    total_tokens = input_tokens + output_tokens
                    emit({"type": "done", "chapter": chapter, "msg": f"《{title}》完成！共{len(state['draft'])}字！耗时{latency/1000:.1f}秒！Token用量：输入{input_tokens} + 输出{output_tokens} = {total_tokens}！"})
                    
                    state["is_committed"] = True

                elif action == "next_chapter":
                    break

                elif action == "complete":
                    break

            # 章间等待（防限流）
            delay = int(toggles.get("inter_chapter_delay", 0) or 0)
            if delay > 0 and not stopped():
                emit({"type": "step", "chapter": chapter, "msg": f"章间等待 {delay} 秒（防限流）..."})
                time.sleep(delay)

            # 弧线级深审 + 摘要压缩（每 5 章）
            if chapter % 5 == 0:
                try:
                    compactor.compact_old_summaries(conn, chapter)
                except Exception:
                    pass

                hooks = truth.get_active_hooks()
                if len(hooks) > 10:
                    emit({"type": "warning", "chapter": chapter, "msg": f"未回收伏笔 {len(hooks)} 个，建议加速回收"})
                overdue = [h for h in hooks.values() if chapter - h.get("plant_chapter", 0) > 15]
                if overdue:
                    emit({"type": "warning", "chapter": chapter,
                          "msg": f"{len(overdue)} 个伏笔已超期15章未回收：{[h['summary'][:20] for h in overdue[:3]]}"})
                climaxes = truth.get_climax_history()
                if climaxes and chapter - climaxes[-1]["chapter"] > 8:
                    emit({"type": "warning", "chapter": chapter, "msg": "距上次高潮超 8 章，建议安排爽点"})

            # 跨章矛盾巡检（每 patrol_interval 章）
            patrol_every = int(toggles.get("patrol_interval", 10) or 10)
            if toggles.get("auto_patrol", True) and patrol_every > 0 and chapter % patrol_every == 0:
                try:
                    emit({"type": "step", "chapter": chapter, "msg": f"正在跨章矛盾巡检（最近{min(patrol_every,15)}章）..."})
                    from engine.patrol import patrol_recent
                    issues = patrol_recent(conn, chapter, lookback=min(patrol_every, 15))
                    if issues:
                        emit({"type": "warning", "chapter": chapter, "msg": f"跨章巡检发现 {len(issues)} 处问题：{'; '.join(issues[:3])}"})
                    else:
                        emit({"type": "step", "chapter": chapter, "msg": "跨章巡检通过：最近章节无明显矛盾"})
                except Exception as e:
                    emit({"type": "warning", "chapter": chapter, "msg": f"巡检失败: {e}"})

        final = crud.get_progress(conn)
        if final.get("current_chapter", 0) >= total_chapters:
            crud.update_progress(conn, status="completed", current_step="done")
            # 自动导出TXT（受开关控制）
            if toggles.get("auto_export", True):
                try:
                    from engine import exporter
                    path = exporter.export_txt(conn, proj_dir, canon.get("title", project_name))
                    emit({"type": "completed", "msg": f"全书 {total_chapters} 章已生成，已导出到 {path}"})
                except Exception as e:
                    emit({"type": "completed", "msg": f"全书 {total_chapters} 章已生成，导出失败: {e}"})
            else:
                emit({"type": "completed", "msg": f"全书 {total_chapters} 章已生成（自动导出已关闭，可手动导出）"})

    except Exception as e:
        import traceback
        traceback.print_exc()
        crud.update_progress(conn, status="failed", current_step=f"error: {str(e)[:100]}")
        emit({"type": "error", "msg": f"引擎崩溃: {str(e)[:200]}"})

    conn.close()
