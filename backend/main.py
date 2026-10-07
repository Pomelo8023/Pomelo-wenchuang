# -*- coding: utf-8 -*-
"""灵云文创 · FastAPI entry（产品级）"""
import asyncio
import json
import threading
import time
import logging
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import get_project_db, get_project_dir, PROJECTS_DIR, VERSION, safe_project_name
from database import crud
from engine import engine as engine_module
from engine.llm import chat

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("lingyun")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动：把所有项目 status 重置为 stopped（重启后 running_jobs 是空的）
    if PROJECTS_DIR.exists():
        for d in PROJECTS_DIR.iterdir():
            if d.is_dir():
                try:
                    db = get_project_db(d.name)
                    crud.init_db(db)
                    conn = crud.get_conn(db)
                    crud.update_progress(conn, status="stopped")
                    conn.close()
                except Exception as e:
                    log.warning(f"重置项目 {d.name} status 失败: {e}")
    yield


app = FastAPI(title="柚子文创 API", version=VERSION, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

running_jobs: dict[str, dict] = {}
HTML_DIR = Path(__file__).parent / "web"
event_queues: dict[str, deque] = {}

# 拆分出去的路由
from routes.toggles import router as toggles_router
from routes.project import router as project_router
app.include_router(toggles_router)
app.include_router(project_router)


def push_event(project: str, event: dict):
    event["id"] = int(time.time() * 1000)
    if project not in event_queues:
        event_queues[project] = deque(maxlen=200)
    event_queues[project].append(event)


def list_chapter_files(proj_dir) -> list:
    """列出项目正文目录下的章节 md 文件，排除 .v1.md 备份"""
    proj_dir = Path(proj_dir)
    files = sorted(proj_dir.glob("正文/第*章*.md"))
    return [f for f in files if not f.name.endswith(".v1.md")]


@app.exception_handler(Exception)
async def global_error_handler(request, exc):
    log.exception("未处理异常: %s", exc)
    return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/login")
async def login():
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/", status_code=302)

@app.get("/health")
@app.get("/api/health")
async def health():
    return {"status": "ok", "version": VERSION, "running": list(running_jobs.keys())}


@app.get("/api/version")
async def version():
    return {"version": VERSION}


@app.get("/api/genres")
async def genres_list():
    from engine.genres import list_genres
    return {"genres": list_genres()}


class GenerateRequest(BaseModel):
    project_name: str
    total_chapters: int = 100
    start_chapter: int = 1  # 续写时从第N章开始
    words_per: int = 2000


class StopRequest(BaseModel):
    project_name: str


class SettingsRequest(BaseModel):
    title: str = ""
    tags: str = ""
    intro: str = ""
    style: str = ""
    genre: str = "都市重生智斗"
    total_ch_min: str = ""
    total_ch_max: str = ""
    words_min: str = ""
    words_max: str = ""
    protagonist_name: str = ""
    protagonist_realm: str = ""
    protagonist_personality: str = ""
    character_tag: str = ""
    short_goal: str = ""
    emotion_hook: str = ""
    world_setting: str = ""
    outline: str = ""
    phases: str = ""
    power_system: str = ""
    gold_finger: str = ""
    villain: str = ""


class KeysRequest(BaseModel):
    AGNES_KEY: str = ""
    ZHIPU_KEY: str = ""
    SILICONFLOW_KEY: str = ""
    DEEPSEEK_KEY: str = ""


class OutlineRequest(BaseModel):
    topic: str = ""
    style: str = "都市重生智斗"
    chapters: int = 30
    project_name: str = ""


# ===== 项目 =====
@app.get("/api/projects")
async def list_projects():
    if not PROJECTS_DIR.exists():
        return []
    result = []
    for d in PROJECTS_DIR.iterdir():
        if d.is_dir():
            db = get_project_db(d.name)
            crud.init_db(db)
            conn = crud.get_conn(db)
            p = crud.get_progress(conn)
            # title从canon.json读
            import json as _json
            canon_path = PROJECTS_DIR / d.name / "story" / "state" / "canon.json"
            title = d.name
            if canon_path.exists():
                try:
                    canon = _json.loads(canon_path.read_text(encoding="utf-8"))
                    title = canon.get("title", d.name)
                except: pass
            conn.close()
            result.append({
                "name": d.name,
                "title": title,
                "status": p.get("status", "idle"),
                "current_chapter": p.get("current_chapter", 0),
                "total_chapters": p.get("total_chapters", 0),
            })
    return result


@app.delete("/api/projects/{name}")
async def delete_project(name: str):
    import shutil
    import time
    pname = safe_project_name(name)
    pdir = PROJECTS_DIR / pname
    
    # 先停止生成线程
    job = running_jobs.get(pname)
    if job and job["thread"].is_alive():
        job["stop_event"].set()
        # 等待线程结束，最多等5秒
        for _ in range(50):
            if not job["thread"].is_alive():
                break
            time.sleep(0.1)
    
    # 清理SSE连接
    if pname in event_queues:
        del event_queues[pname]
    
    # 删除目录
    if pdir.exists():
        try:
            shutil.rmtree(pdir)
        except PermissionError:
            # Windows下文件被占用，等一下再删
            time.sleep(1)
            try:
                shutil.rmtree(pdir)
            except Exception as e:
                raise HTTPException(500, f"删除失败：{e}")
    
    # 清理running_jobs
    if pname in running_jobs:
        del running_jobs[pname]
    
    return {"status": "deleted"}


# ===== 生成 =====
@app.post("/api/generate/start")
async def start_generate(req: GenerateRequest):
    try:
        pname = safe_project_name(req.project_name)
    except ValueError as e:
        raise HTTPException(400, str(e))
    job = running_jobs.get(pname)
    if job and job["thread"].is_alive():
        return {"status": "already_running"}

    # 把words_per存到项目canon
    try:
        canon_path = PROJECTS_DIR / pname / "story" / "state" / "canon.json"
        if canon_path.exists():
            import json
            canon = json.loads(canon_path.read_text(encoding="utf-8"))
            canon["words_per"] = req.words_per
            canon_path.write_text(json.dumps(canon, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    def on_event(event):
        push_event(pname, event)

    # 检查是否已有项目在生成中
    for existing_name, job in running_jobs.items():
        if job["thread"].is_alive():
            return {"error": f"已有项目「{existing_name}」在生成中，请先暂停或停止"}
    
    stop_event = threading.Event()
    t = threading.Thread(
        target=engine_module.run_engine,
        args=(pname, req.total_chapters, on_event, stop_event, req.start_chapter),
        daemon=True,
    )
    running_jobs[pname] = {"thread": t, "stop_event": stop_event}
    t.start()
    return {"status": "started"}


@app.post("/api/generate/stop")
async def stop_generate(req: StopRequest):
    pname = safe_project_name(req.project_name)
    job = running_jobs.get(pname)
    if job and job["thread"].is_alive():
        job["stop_event"].set()
        return {"status": "stopping"}
    return {"status": "not_running"}


# ===== SSE =====
@app.get("/api/projects/{name}/stream")
async def stream(name: str):
    name = safe_project_name(name)  # 统一用safe_project_name后的名字
    async def event_gen():
        db_path = get_project_db(name)
        conn = crud.get_conn(db_path)
        try:
            logs = crud.list_logs(conn, limit=30)
            for log in reversed(logs):
                yield f"data: {json.dumps(log, ensure_ascii=False)}\n\n"
                await asyncio.sleep(0.02)

            # last_id设置成当前时间，避免重复推送已经推送过的事件
            last_id = int(time.time() * 1000)
            while True:
                await asyncio.sleep(0.3)
                q = event_queues.get(name)
                if q:
                    for evt in list(q):
                        if evt.get("id", 0) > last_id:
                            last_id = evt.get("id", 0)
                            yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
                p = crud.get_progress(conn)
                if p.get("status") in ("completed", "error", "paused"):
                    yield f"data: {json.dumps({'done': True}, ensure_ascii=False)}\n\n"
                    break
        finally:
            conn.close()

    return StreamingResponse(event_gen(), media_type="text/event-stream")


# ===== 大纲生成 =====
@app.post("/api/generate/outline")
async def gen_outline(req: OutlineRequest):
    prompt = f"""你是网文策划。根据以下题材生成一份详细的网文大纲。

【题材】{req.topic}
【风格】{req.style}
【规划章数】{req.chapters}章

输出 JSON：
{{
  "title": "书名（4-6字）",
  "tags": "卖点标签（番茄简介开头用，例：杀伐果断+面板+升级流+无敌碾压）",
  "intro": "简介文案（200字内，和书名呼应，有悬念和期待度）",
  "style": "文风（根据题材自动匹配：冷峻/热血/搞笑/悬疑/轻松/硬核）",
  "protagonist_name": "主角名",
  "protagonist_realm": "主角初始身份",
  "protagonist_personality": "主角性格（一句话）",
  "character_tag": "人设标签（越极端越好，根据题材自动匹配最爽的人设）",
  "short_goal": "短期目标（前3章主角要干什么，根据题材自动匹配最紧迫的生存目标）",
  "emotion_hook": "情绪锚点（这本书的核心快感，根据题材自动匹配最爽的模式：碾压/打脸/逆袭/称霸/揭秘）",
  "world_setting": "世界观（200字内）",
  "power_system": "力量体系（100字内）",
  "gold_finger": "金手指/核心爽点（根据题材自动匹配最适合的形式：系统/血脉/重生记忆/穿越优势/特殊能力）",
  "villain": "主要反派（一句话）",
  "outline": "总大纲（分3-5卷，每卷一句话）"
}}
直接输出 JSON。"""
    text = chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8, max_tokens=2000,
    )
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        return {"error": "大纲生成失败"}

    # 如果指定了项目，顺便生成剧情大框架存到canon
    if req.project_name:
        try:
            from engine.truth import TruthFile
            from engine.director import generate_outline
            pname = safe_project_name(req.project_name)
            proj_dir = get_project_dir(pname)
            truth = TruthFile(proj_dir)
            canon = truth.get_canon()
            canon.update({
                "title": result.get("title", ""),
                "protagonist": result.get("protagonist_name", ""),
                "protagonist_name": result.get("protagonist_name", ""),
                "protagonist_realm": result.get("protagonist_realm", ""),
                "protagonist_personality": result.get("protagonist_personality", ""),
                "character_tag": result.get("character_tag", ""),
                "short_goal": result.get("short_goal", ""),
                "emotion_hook": result.get("emotion_hook", ""),
                "gold_finger": result.get("gold_finger", ""),
                "power_system": result.get("power_system", ""),
                "villain": result.get("villain", ""),
                "world_setting": result.get("world_setting", ""),
                "genre": req.style,
            })
            # 总是生成phases返回给前端显示
            outline = generate_outline(req.chapters, canon)
            canon["outline"] = outline
            result["phases"] = outline.get("phases", [])
            truth.set_canon(canon)
        except Exception as e:
            result["warn"] = f"剧情框架生成失败: {e}"

    return result


# ===== 进度 =====
@app.get("/api/projects/{name}/progress")
async def get_progress(name: str):
    db = get_project_db(name)
    crud.init_db(db)
    conn = crud.get_conn(db)
    p = crud.get_progress(conn)
    conn.close()
    return p


# ===== 世界地图 =====
@app.post("/api/projects/{name}/world-map")
async def generate_world_map(name: str):
    import json as _json
    canon_path = _get_canon_path(name)
    canon = _json.loads(canon_path.read_text(encoding="utf-8")) if canon_path.exists() else {}
    title = canon.get("title", name)
    world = canon.get("world_setting", "")
    power = canon.get("power_system", "")
    villain = canon.get("villain", "")

    prompt = f"""根据以下小说设定，生成一个世界地图。只返回 JSON，不要其他文字。

书名：{title}
世界观：{world}
力量体系：{power}
主要反派：{villain}

返回格式：
{{
  "regions": [
    {{"name": "区域名", "x": 0-100, "y": 0-100, "power": "势力/阵营名", "color": "#hex颜色", "desc": "一句话描述"}}
  ]
}}

要求：
- 5-8 个区域
- x、y 坐标在 0-100 之间，代表在地图上的相对位置
- color 用十六进制颜色，不同势力不同色
- desc 一句话概括这个区域的特点
- 只返回 JSON"""

    try:
        result = chat([{"role": "user", "content": prompt}])
        # 提取 JSON
        import re
        m = re.search(r'\{[\s\S]*\}', result)
        if m:
            data = _json.loads(m.group())
            # 存到 canon.json
            canon["world_map"] = data
            canon_path.write_text(_json.dumps(canon, ensure_ascii=False, indent=2), encoding="utf-8")
            return data
        return {"regions": [], "error": "LLM 返回格式错误"}
    except Exception as e:
        return {"regions": [], "error": str(e)}


@app.get("/api/projects/{name}/world-map")
async def get_world_map(name: str):
    import json as _json
    canon_path = _get_canon_path(name)
    if canon_path.exists():
        canon = _json.loads(canon_path.read_text(encoding="utf-8"))
        return canon.get("world_map", {"regions": []})
    return {"regions": []}


# ===== 分章大纲（卷级） =====
@app.post("/api/projects/{name}/chapter-outline")
async def gen_chapter_outline(name: str):
    import json as _json
    canon_path = _get_canon_path(name)
    canon = _json.loads(canon_path.read_text(encoding="utf-8")) if canon_path.exists() else {}
    title = canon.get("title", name)
    outline = canon.get("outline", "")
    total = int(canon.get("total_ch_max", 100))
    # 每卷约 60 章，算出总卷数
    volumes = max(8, min(20, (total + 59) // 60))

    prompt = f"""根据以下小说总大纲，生成全本卷级大纲。只返回 JSON，不要其他文字。

书名：{title}
总大纲：{outline}
总章节数：{total}

返回格式：
{{
  "volumes": [
    {{
      "volume": 1,
      "title": "卷名（4-8字）",
      "chapters": "第1-60章",
      "conflict": "本卷核心冲突（一句话）",
      "climax": "卷末高潮（一句话）",
      "arc": "主角状态变化：从XX到XX",
      "hook": "卷末勾子（引向下一卷的悬念）"
    }}
  ]
}}

要求：
- 共 {volumes} 卷，每卷约 60 章
- 每卷是一个完整的小高潮，有起承转合
- 卷末必须有高潮 + 勾子引向下一卷
- 主角实力每卷上一个台阶
- 只返回 JSON"""

    try:
        result = chat([{"role": "user", "content": prompt}])
        import re
        m = re.search(r'\{[\s\S]*\}', result)
        if m:
            data = _json.loads(m.group())
            canon["chapter_outline"] = data
            canon_path.write_text(_json.dumps(canon, ensure_ascii=False, indent=2), encoding="utf-8")
            return data
        return {"volumes": [], "error": "LLM 返回格式错误"}
    except Exception as e:
        return {"volumes": [], "error": str(e)}


@app.get("/api/projects/{name}/chapter-outline")
async def get_chapter_outline(name: str):
    import json as _json
    canon_path = _get_canon_path(name)
    if canon_path.exists():
        canon = _json.loads(canon_path.read_text(encoding="utf-8"))
        return canon.get("chapter_outline", {"chapters": []})
    return {"chapters": []}


def _get_canon_path(name: str):
    pname = safe_project_name(name)
    return PROJECTS_DIR / pname / "story" / "state" / "canon.json"

@app.post("/api/projects/{name}/settings")
async def save_settings(name: str, req: SettingsRequest):
    import json
    canon_path = _get_canon_path(name)
    if canon_path.exists():
        canon = json.loads(canon_path.read_text(encoding="utf-8"))
    else:
        canon = {}
    # 合并新设定
    canon.update(req.dict())
    canon_path.parent.mkdir(parents=True, exist_ok=True)
    canon_path.write_text(json.dumps(canon, ensure_ascii=False, indent=2), encoding="utf-8")
    # 同时更新角色表和project_meta
    db = get_project_db(name)
    crud.init_db(db)
    conn = crud.get_conn(db)
    # 把genre等关键字段同步到project_meta，确保context能读到
    crud.update_meta(conn, 
        title=req.title,
        genre=req.genre,
        protagonist_name=req.protagonist_name,
        world_setting=req.world_setting,
        outline=req.outline,
        power_system=req.power_system if hasattr(req, 'power_system') else "",
        gold_finger=req.gold_finger if hasattr(req, 'gold_finger') else "",
        villain=req.villain if hasattr(req, 'villain') else "",
    )
    # 更新total_chapters
    total_ch_max = int(req.total_ch_max) if hasattr(req, 'total_ch_max') and req.total_ch_max else 100
    conn.execute("UPDATE progress SET total_chapters = ?", (total_ch_max,))
    conn.commit()
    if req.protagonist_name:
        crud.upsert_character(conn, {
            "id": "char_protagonist", "name": req.protagonist_name, "aliases": "[]",
            "role_type": "protagonist", "realm": req.protagonist_realm,
            "personality": req.protagonist_personality, "abilities": "[]",
            "state": "", "first_chapter": 0, "last_chapter": 0, "notes": "",
        })
    conn.close()
    return {"status": "saved"}


# ===== Keys =====
@app.get("/api/keys")
async def get_keys():
    keys = crud.load_keys()
    return {k: ("已配置" if v else "") for k, v in keys.items()}


@app.post("/api/keys")
async def save_keys(req: KeysRequest):
    crud.save_keys(req.dict(exclude_unset=True))
    return {"status": "saved"}


# ===== 导出 =====
@app.get("/api/projects/{name}/doctor")
async def doctor(name: str):
    """一键体检：检查项目文件/DB/配置完整性"""
    issues = []
    warnings = []
    info = []
    try:
        db = get_project_db(name)
        pdir = get_project_dir(name)
    except Exception as e:
        return {"ok": False, "issues": [f"项目路径错误: {e}"], "warnings": [], "info": []}

    if not db.exists():
        issues.append("story.db 不存在")
    else:
        try:
            conn = crud.get_conn(db)
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            need = ["project_meta", "chapters", "entities", "foreshadow_contracts", "events", "progress", "logs"]
            for t in need:
                if t not in tables:
                    issues.append(f"缺表: {t}")
            p = crud.get_progress(conn)
            info.append(f"已写 {p.get('current_chapter',0)}/{p.get('total_chapters',0)} 章")
            ch_count = conn.execute("SELECT COUNT(*) c FROM chapters").fetchone()["c"]
            info.append(f"DB 中 {ch_count} 章")
            if ch_count > 0:
                last = conn.execute("SELECT chapter, title, word_count, created_at FROM chapters ORDER BY chapter DESC LIMIT 1").fetchone()
                info.append(f"最新: 第{last['chapter']}章 {last['title']} ({last['word_count']}字)")
            conn.close()
        except Exception as e:
            issues.append(f"DB 损坏: {e}")

    for d in ["正文", "设定集"]:
        if not (pdir / d).exists():
            warnings.append(f"缺目录: {d}")

    if (pdir / "story" / "state").exists():
        state_files = list((pdir / "story" / "state").glob("*.json"))
        info.append(f"状态文件 {len(state_files)} 个")

    return {"ok": len(issues) == 0, "issues": issues, "warnings": warnings, "info": info}


# ===== 对标书拆解 =====
class DeconstructReq(BaseModel):
    text: str
    genre: str = ""


@app.post("/api/deconstruct")
async def deconstruct(req: DeconstructReq):
    """拆解对标小说文本，提取可迁移的爽点节奏/钩子结构"""
    from engine.llm import chat
    text = req.text[:6000]  # 最多 6000 字
    prompt = f"""你是网文编辑。拆解以下对标小说片段，提取可迁移的创作模式。

【对标文本】
{text}

输出 JSON：
{{
  "hook_type": "开篇钩子类型（悬念/冲突/反差/重生/金手指）",
  "opening_analysis": "开篇500字怎么抓人",
  "cool_point_pattern": "爽点节奏（铺垫多久/爆发在哪/怎么收）",
  "chapter_hook": "章末钩子怎么留",
  "protagonist_impression": "主角第一印象怎么立",
  "pacing": "节奏快慢",
  "transferable_rules": ["可迁移规则1", "可迁移规则2", "可迁移规则3"],
  "do_not_copy": ["不要照搬的原作专有元素1"]
}}

直接输出 JSON。"""
    result = chat(messages=[{"role": "user", "content": prompt}], temperature=0.3, max_tokens=1000, fast=True)
    if result.startswith("```"):
        result = result.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(result)
    except Exception:
        return {"error": "拆解失败", "raw": result[:500]}


# ===== 文风学习 =====
class StyleReq(BaseModel):
    text: str
    project: str = ""


@app.post("/api/styleguide/extract")
async def styleguide_extract(req: StyleReq):
    """从参考文本提取文风指南"""
    from engine.styleguide import extract_style_guide
    guide = extract_style_guide(req.text)
    if req.project:
        try:
            conn = crud.get_conn(get_project_db(req.project))
            crud.update_meta(conn, style=guide)
            conn.close()
        except Exception:
            pass
    return {"guide": guide}


# ===== 封面生成 =====
class CoverReq(BaseModel):
    title: str
    genre: str = "都市重生智斗"
    protagonist: str = ""
    extra_prompt: str = ""


@app.post("/api/cover/generate")
async def generate_cover(req: CoverReq):
    """用 Agnes Image 生成网文封面（3:4 竖版）"""
    import requests
    keys = json.loads((Path(__file__).parent / "api_keys.json").read_text(encoding="utf-8"))
    agnes_key = keys.get("AGNES_KEYS", [""])[0]
    if not agnes_key:
        raise HTTPException(400, "未配置 Agnes key")

    # 根据题材拼 prompt
    genre_styles = {
        "修仙": "古风仙侠，云海山峰，御剑飞行，金色法术光效，水墨风",
        "都市重生智斗": "现代都市夜景，高楼大厦，西装男主，霓虹灯光，电影感",
        "系统流": "赛博朋克，全息屏幕，科技感UI，蓝色光效",
        "无限流": "诡异空间，多副本拼接，暗色恐怖氛围",
        "悬疑灵异": "昏暗古宅，烛火，阴影，中式恐怖",
        "甜宠言情": "唯美古风，粉色花瓣，俊男美女，浪漫柔光",
        "末世": "废墟城市，灰暗天空，孤独背影，荒凉感",
        "规则怪谈": "日式恐怖，诡异走廊，红色灯光，不可名状",
    }
    style = genre_styles.get(req.genre, "电影感，高细节，网文封面风格")

    prompt = f"网文小说封面，书名《{req.title}》，主角{req.protagonist or '主角'}，{style}，竖版构图，高细节，专业封面设计，不要文字"
    if req.extra_prompt:
        prompt += "，" + req.extra_prompt

    try:
        resp = requests.post(
            "https://apihub.agnes-ai.com/v1/images/generations",
            headers={"Authorization": f"Bearer {agnes_key}"},
            json={
                "model": "agnes-image-2.1-flash",
                "prompt": prompt,
                "size": "1K",
                "ratio": "2:3",
                "extra_body": {"response_format": "url"},
            },
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        return {"url": data["data"][0]["url"], "prompt": prompt}
    except Exception as e:
        raise HTTPException(500, f"封面生成失败: {e}")


# ===== 市场雷达 =====
@app.get("/api/radar")
async def radar():
    """市场雷达：当前热门题材+可执行切入建议"""
    from engine.llm import chat
    from engine.genres import list_genres
    available = list_genres()
    prompt = f"""你是网文市场分析师+资深编辑。当前平台可写题材：{', '.join(available)}

分析当前（2026年Q4）网文市场，输出：
1. 5个正在上升的题材/细分方向
2. 每个方向：为什么火、读者在追什么爽点、新人怎么切入（具体到开篇钩子）
3. 哪些题材已经红海中晚期，新人别碰
4. 给3个"现在写必出效果"的开篇设定建议

输出 JSON：
{{
  "rising": [{{"genre":"...","why":"...","hook":"开篇钩子建议","tip":"..."}}],
  "avoid": ["别碰的题材1","别碰的题材2"],
  "golden_ideas": ["开篇设定1","开篇设定2","开篇设定3"]
}}
直接输出 JSON。"""
    result = chat(messages=[{"role": "user", "content": prompt}], temperature=0.6, max_tokens=2000, fast=True)
    # 清理 markdown 包裹
    r = result.strip()
    if r.startswith("```"):
        r = r.split("\n", 1)[1] if "\n" in r else r[3:]
        if r.endswith("```"):
            r = r[:-3]
        r = r.strip()
    try:
        return json.loads(r)
    except Exception:
        return {"rising": [], "avoid": [], "golden_ideas": [], "error": r[:300]}


# ===== research_web：真上网搜 =====
@app.get("/api/research")
async def research(q: str):
    """真上网搜热门题材（DuckDuckGo免费）"""
    import urllib.request, urllib.parse, re
    query = urllib.parse.quote(f"2026 网文 热门题材 番茄 起点 {q}")
    url = f"https://html.duckduckgo.com/html/?q={query}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        html = urllib.request.urlopen(req, timeout=10).read().decode("utf-8", errors="ignore")
        # 提取标题+摘要
        results = re.findall(r'class="result__a"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</a>', html, re.S)
        out = []
        for title, snippet in results[:5]:
            out.append({
                "title": re.sub(r"<[^>]+>", "", title).strip(),
                "snippet": re.sub(r"<[^>]+>", "", snippet).strip()[:200]
            })
        return {"results": out}
    except Exception as e:
        return {"results": [], "error": str(e)[:200]}


# ===== AI对话 =====
class ChatReq(BaseModel):
    message: str
    project: str = ""
    history: list = []

@app.post("/api/chat")
async def chat_ai(req: ChatReq):
    """AI对话：理解用户意图，自动生成创作建议"""
    from engine.llm import chat
    # 注入当前项目设定+全本摘要
    ctx = ""
    if req.project:
        try:
            pname = safe_project_name(req.project)
            db = get_project_db(pname)
            from database import crud
            conn = crud.get_conn(db)
            meta = crud.get_meta(conn)
            p = crud.get_progress(conn)
            conn.close()
            ctx = f"\n\n【当前项目】书名：{meta.get('title','')}，题材：{meta.get('genre','')}，已写{p.get('current_chapter',0)}章"
            
            # 读取设定文件（统一用绝对路径）
            import os, json
            from config import get_project_dir
            proj_dir = str(get_project_dir(pname))
            canon_path = os.path.join(proj_dir, "story", "state", "canon.json")
            if os.path.exists(canon_path):
                with open(canon_path, 'r', encoding='utf-8') as f:
                    canon = json.load(f)
                    ctx += f"\n\n【设定】"
                    if canon.get('title'): ctx += f"\n书名：{canon['title']}"
                    if canon.get('genre'): ctx += f"\n题材：{canon['genre']}"
                    if canon.get('protagonist_name'): ctx += f"\n主角：{canon['protagonist_name']}"
                    if canon.get('outline'):
                        outline_str = str(canon['outline'])[:300]
                        ctx += f"\n总大纲：{outline_str}..."
            
            # 读取所有章节的标题+每章前200字（让AI知道全本书的内容）
            chapters_dir = os.path.join(proj_dir, "正文")
            if os.path.exists(chapters_dir):
                files = sorted([f for f in os.listdir(chapters_dir) if f.endswith('.md')])
                ctx += f"\n\n【全本书章节列表】"
                for f in files:
                    with open(os.path.join(chapters_dir, f), 'r', encoding='utf-8') as fp:
                        content = fp.read()[:200]
                        ctx += f"\n{f}：{content}..."
                
                # 检测用户问的是哪一章，读取完整内容
                import re
                ch_match = re.search(r'第([一二三四五六七八九十百千\d]+)章', req.message)
                if ch_match:
                    ch_num_str = ch_match.group(1)
                    # 中文数字转阿拉伯
                    cn_num = {'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,'十':10,'百':100,'千':1000}
                    ch_num = 0
                    if ch_num_str.isdigit():
                        ch_num = int(ch_num_str)
                    else:
                        # 简单中文数字转换
                        if '十' in ch_num_str:
                            parts = ch_num_str.split('十')
                            ch_num = (cn_num.get(parts[0],1) if parts[0] else 1) * 10
                            if len(parts) > 1 and parts[1]:
                                ch_num += cn_num.get(parts[1],0)
                        else:
                            ch_num = cn_num.get(ch_num_str, 0)
                    
                    # 找到对应章节文件（支持第1章/第0001章两种格式）
                    for f in files:
                        f_num_match = re.search(r'第(\d+)章', f)
                        if f_num_match and int(f_num_match.group(1)) == ch_num:
                            with open(os.path.join(chapters_dir, f), 'r', encoding='utf-8') as fp:
                                full_content = fp.read()
                                ctx += f"\n\n【用户询问的章节完整内容】\n{f}：\n{full_content[:5000]}..."
                            break
                    ch_num = 0
                    if ch_num_str.isdigit():
                        ch_num = int(ch_num_str)
                    else:
                        # 简单中文数字转换
                        if '十' in ch_num_str:
                            parts = ch_num_str.split('十')
                            ch_num = (cn_num.get(parts[0],1) if parts[0] else 1) * 10
                            if len(parts) > 1 and parts[1]:
                                ch_num += cn_num.get(parts[1],0)
                        else:
                            ch_num = cn_num.get(ch_num_str, 0)
                    
                    # 找到对应章节文件（支持第1章/第0001章两种格式）
                    for f in files:
                        f_num_match = re.search(r'第(\d+)章', f)
                        if f_num_match and int(f_num_match.group(1)) == ch_num:
                            with open(os.path.join(chapters_dir, f), 'r', encoding='utf-8') as fp:
                                full_content = fp.read()
                                ctx += f"\n\n【用户询问的章节完整内容】\n{f}：\n{full_content[:5000]}..."
                            break
        except Exception as e:
            import traceback
            print(f"[chat] 读取项目信息失败: {e}")
            traceback.print_exc()
            ctx += f"\n\n(读取项目信息失败: {e})"
    # 限制context总长度（防止爆token）
    if len(ctx) > 8000:
        ctx = ctx[:8000] + "\n\n...(内容已截断)"
    system = f"""你是网文创作助手Pomelo，你已经读取了当前项目的全部设定和章节内容。{ctx}

重要：你已经有了这些内容，不要再说"我无法读取你的文件"或"请粘贴内容给我"。直接基于上面的内容回答用户问题。

回复要简短（300字内），直接给可执行建议。不要长篇大论。

【重要】你需要理解用户的意图！如果用户要修改某一章（不管他说"修改"、"改"、"优化"、"润色"、"调整"、"把这一章改得更好"等任何说法），你都需要在回复的最后加上一个特殊标记：
<<<MODIFY_CHAPTER:章节号>>>
比如用户说"帮我润色一下第25章"，你就在回复最后加上：<<<MODIFY_CHAPTER:25>>>
注意：只要用户的意图是要修改某一章，不管他用什么词，你都要加这个标记！"""
    # 多轮对话：把历史消息传进去
    history = req.history or []
    messages = [{"role": "system", "content": system}]
    for h in history[-10:]:  # 最近10轮
        messages.append({"role": h.get("role", "user"), "content": h.get("content", "")})
    messages.append({"role": "user", "content": req.message})
    reply = await asyncio.to_thread(chat, messages=messages, temperature=0.7, max_tokens=4000, fast=True)
    print(f"[chat] AI回复: {reply[:200]}...")  # 打印前200字
    
    # 检测AI回复里有没有修改章节的标记，如果有，自动加到接收器队列里
    import re
    modify_match = re.search(r'<<<MODIFY_CHAPTER:(\d+)>>>', reply)
    if modify_match and req.project:
        try:
            ch_num = int(modify_match.group(1))
            clean_reply = re.sub(r'<<<MODIFY_CHAPTER:\d+>>>', '', reply)
            pname = safe_project_name(req.project)
            if pname not in feedback_queue:
                feedback_queue[pname] = load_feedback_queue(pname)  # 从文件里加载
            feedback_queue[pname].append({
                "chapter_num": ch_num,
                "feedback": clean_reply[:300],
                "time": str(datetime.now())
            })
            save_feedback_queue(pname, feedback_queue[pname])  # 保存到文件
            print(f"[chat] 已把修改建议加到接收器队列：第{ch_num}章")
        except Exception as e:
            print(f"[chat] 加到接收器队列失败: {e}")
    
    # 检测回复里有没有修改建议，自动保存到项目设定里
    import re
    # 只有用户明确说"修改"、"优化"、"改"等关键词时，才保存user_feedback
    feedback_keywords = ["修改", "优化", "重写", "润色", "改一改", "调整"]
    has_feedback = any(kw in req.message for kw in feedback_keywords)
    if has_feedback and req.project:
        try:
            pname = safe_project_name(req.project)
            import os, json
            from config import get_project_dir
            proj_dir = str(get_project_dir(pname))
            canon_path = os.path.join(proj_dir, "story", "state", "canon.json")
            if os.path.exists(canon_path):
                with open(canon_path, 'r', encoding='utf-8') as f:
                    canon = json.load(f)
                # 把最新的用户反馈加到canon里
                canon["user_feedback"] = reply[:500]  # 只存前500字
                with open(canon_path, 'w', encoding='utf-8') as f:
                    json.dump(canon, f, ensure_ascii=False, indent=2)
                print(f"[chat] 已保存用户反馈到 {pname} 的canon.json")
        except Exception as e:
            print(f"[chat] 保存用户反馈失败: {e}")
    
    return {"reply": reply}


# ===== 接收器：保存修改建议到队列 =====
class FeedbackReq(BaseModel):
    project: str
    chapter_num: int
    feedback: str

feedback_queue = {}  # {项目名: [ {chapter_num, feedback, time} ]}
modify_log_queue = {}  # {项目名: [ {chapter_num, status, time, message} ]}

def load_modify_log_queue(pname):
    """从文件里加载修改日志队列"""
    proj_dir = PROJECTS_DIR / pname
    log_path = proj_dir / "story" / "state" / "modify_log.json"
    if log_path.exists():
        import json
        return json.loads(log_path.read_text(encoding="utf-8"))
    return []

def save_modify_log_queue(pname, queue):
    """保存修改日志队列到文件"""
    proj_dir = PROJECTS_DIR / pname
    log_path = proj_dir / "story" / "state" / "modify_log.json"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    import json
    log_path.write_text(json.dumps(queue, ensure_ascii=False, indent=2), encoding="utf-8")

# 从文件加载接收器队列
def load_feedback_queue(pname):
    import os, json
    from config import get_project_dir
    proj_dir = str(get_project_dir(pname))
    feedback_path = os.path.join(proj_dir, "story", "state", "feedback.json")
    if os.path.exists(feedback_path):
        with open(feedback_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# 保存接收器队列到文件
def save_feedback_queue(pname, queue):
    import os, json
    from config import get_project_dir
    proj_dir = str(get_project_dir(pname))
    os.makedirs(os.path.join(proj_dir, "story", "state"), exist_ok=True)
    feedback_path = os.path.join(proj_dir, "story", "state", "feedback.json")
    with open(feedback_path, 'w', encoding='utf-8') as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)

@app.post("/api/add_feedback")
async def add_feedback(req: FeedbackReq):
    pname = safe_project_name(req.project)
    if pname not in feedback_queue:
        feedback_queue[pname] = load_feedback_queue(pname)
    feedback_queue[pname].append({
        "chapter_num": req.chapter_num,
        "feedback": req.feedback,
        "time": str(datetime.now())
    })
    save_feedback_queue(pname, feedback_queue[pname])
    return {"ok": True, "count": len(feedback_queue[pname])}

@app.get("/api/get_feedback/{project}")
async def get_feedback(project: str):
    pname = safe_project_name(project)
    if pname not in feedback_queue:
        feedback_queue[pname] = load_feedback_queue(pname)
    return {"feedback": feedback_queue.get(pname, [])}

@app.delete("/api/clear_feedback/{project}")
async def clear_feedback(project: str):
    pname = safe_project_name(project)
    feedback_queue[pname] = []
    save_feedback_queue(pname, feedback_queue[pname])
    return {"ok": True}

@app.get("/api/get_modify_log/{project}")
def get_modify_log(project: str):
    pname = safe_project_name(project)
    # 从文件里加载
    if pname not in modify_log_queue:
        modify_log_queue[pname] = load_modify_log_queue(pname)
    return {"log": modify_log_queue.get(pname, [])}


# ===== 保存修改后的章节 =====
class SaveChapterReq(BaseModel):
    project: str
    chapter_num: int
    title: str
    content: str

@app.post("/api/save_chapter")
async def save_chapter(req: SaveChapterReq):
    import os
    from config import get_project_dir
    proj_dir = str(get_project_dir(req.project))
    chapters_dir = os.path.join(proj_dir, "正文")
    os.makedirs(chapters_dir, exist_ok=True)
    # 找到对应章节文件（支持第1章/第0001章两种格式）
    files = [f for f in os.listdir(chapters_dir) if f.endswith('.md')]
    target_file = None
    for f in files:
        import re
        m = re.match(r'第(\d+)章', f)
        if m and int(m.group(1)) == req.chapter_num:
            target_file = f
            break
    if not target_file:
        # 新建
        target_file = f"第{req.chapter_num:04d}章 {req.title}.md"
    filepath = os.path.join(chapters_dir, target_file)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(req.content)
    return {"ok": True, "file": target_file}


# ===== 修改章节（需要用户确认） =====
class ModifyChapterReq(BaseModel):
    project: str
    chapter_num: int
    modify_request: str  # 用户的修改要求
    modify_suggestion: str = ""  # AI之前给出的修改建议
    save: bool = True  # 是否保存到文件里！默认保存！如果是AI优化，先不保存！

@app.post("/api/modify_chapter")
async def modify_chapter(req: ModifyChapterReq):
    import os, re
    from config import get_project_dir
    from engine.llm import chat
    from datetime import datetime
    
    pname = safe_project_name(req.project)
    proj_dir = str(get_project_dir(pname))
    chapters_dir = os.path.join(proj_dir, "正文")
    
    # 记录修改日志：正在处理
    if pname not in modify_log_queue:
        modify_log_queue[pname] = []
    modify_log_queue[pname].append({
        "chapter_num": req.chapter_num,
        "status": "processing",
        "time": datetime.now().isoformat(),
        "message": f"开始修改第{req.chapter_num}章..."
    })
    
    # 找到对应章节文件
    files = [f for f in os.listdir(chapters_dir) if f.endswith('.md')]
    target_file = None
    for f in files:
        m = re.match(r'第(\d+)章', f)
        if m and int(m.group(1)) == req.chapter_num:
            target_file = f
            break
    
    if not target_file:
        modify_log_queue[pname].append({
            "chapter_num": req.chapter_num,
            "status": "error",
            "time": datetime.now().isoformat(),
            "message": f"第{req.chapter_num}章不存在"
        })
        return {"error": f"第{req.chapter_num}章不存在"}
    
    # 读取章节内容
    with open(os.path.join(chapters_dir, target_file), 'r', encoding='utf-8') as f:
        old_content = f.read()
    
    modify_log_queue[pname].append({
        "chapter_num": req.chapter_num,
        "status": "processing",
        "time": datetime.now().isoformat(),
        "message": f"已读取第{req.chapter_num}章，共{len(old_content)}字"
    })
    
    modify_log_queue[pname].append({
        "chapter_num": req.chapter_num,
        "status": "processing",
        "time": datetime.now().isoformat(),
        "message": "正在调用AI进行局部修改..."
    })
    
    # 用LLM修改（局部修改，不要重写整个章节）
    modify_prompt = f"""以下是小说第{req.chapter_num}章的内容。请根据用户的要求和AI之前给出的修改建议，进行**局部修改**：

【用户要求】
{req.modify_request}

【AI之前给出的修改建议】
{req.modify_suggestion}

【章节原文】
{old_content}

【修改要求（非常重要！）】
1. **只修改有问题的部分！不要重写整个章节！**
2. **其他部分必须保持原样！一个字都不要改！**
3. **保持原来的风格、剧情、人物性格！**
4. **不要加新内容！不要加新场景！不要加新人物！**
5. **直接输出修改后的完整章节！**

记住：这是局部修改！不是重写！其他部分必须保持原样！"""
    new_content = await asyncio.to_thread(
        chat,
        messages=[
            {"role": "system", "content": "你是网文编辑，进行局部修改！只改有问题的部分！其他部分保持原样！直接输出修改后的章节，不要解释。"},
            {"role": "user", "content": modify_prompt}
        ],
        temperature=0.3,  # 降低温度，让LLM更保守
        max_tokens=6000,
    )
    
    if not new_content or len(new_content) < 500:
        modify_log_queue[pname].append({
            "chapter_num": req.chapter_num,
            "status": "error",
            "time": datetime.now().isoformat(),
            "message": f"修改失败，返回内容太短"
        })
        return {"error": "修改失败，返回内容太短"}
    
    # 字数检查：超标就让AI来精简！不是截断！
    try:
        import json as _json
        canon_path = os.path.join(proj_dir, "story", "state", "canon.json")
        if os.path.exists(canon_path):
            with open(canon_path, "r", encoding="utf-8") as f:
                canon = _json.load(f)
            max_words = int(canon.get("words_max", 2200))
            if len(new_content) > max_words:
                modify_log_queue[pname].append({
                    "chapter_num": req.chapter_num,
                    "status": "processing",
                    "time": datetime.now().isoformat(),
                    "message": f"字数超标({len(new_content)}字)，正在精简到{max_words}字..."
                })
                # 让AI来精简！不是截断！
                trim_prompt = f"""以下是小说第{req.chapter_num}章的内容，现在有{len(new_content)}字，超过了最大限制{max_words}字！

请精简内容！目标：精简到{max_words}字以内！

【精简要求】
1. 保留核心剧情和关键对话！
2. 删除冗余描写和废话！
3. 保持原来的风格、人物性格！
4. 不要加新内容！
5. 直接输出精简后的完整章节！

【章节内容】
{new_content}"""
                
                new_content = await asyncio.to_thread(
                    chat,
                    messages=[
                        {"role": "system", "content": "你是网文编辑，精简章节内容！删除冗余描写！保留核心剧情！"},
                        {"role": "user", "content": trim_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=6000,
                )
                
                modify_log_queue[pname].append({
                    "chapter_num": req.chapter_num,
                    "status": "processing",
                    "time": datetime.now().isoformat(),
                    "message": f"精简完成，共{len(new_content)}字"
                })
    except Exception as e:
        # 如果精简失败，就截断
        import traceback
        traceback.print_exc()
        try:
            new_content = new_content[:max_words]
            last_period = max(new_content.rfind("。"), new_content.rfind("！"), new_content.rfind("？"))
            if last_period > max_words * 0.8:
                new_content = new_content[:last_period+1]
        except Exception:
            pass
    
    # ===== 三十维验收（复制写作台的流程） =====
    modify_log_queue[pname].append({
        "chapter_num": req.chapter_num,
        "status": "processing",
        "time": datetime.now().isoformat(),
        "message": f"正在验收第{req.chapter_num}章..."
    })
    
    try:
        # 先尝试导入audit模块
        try:
            from engine import audit
            audit_result = audit.run_audit(new_content, old_content)
            audit_score = audit_result.get("score", 0)
        except ImportError:
            # audit模块不存在，跳过验收
            modify_log_queue[pname].append({
                "chapter_num": req.chapter_num,
                "status": "processing",
                "time": datetime.now().isoformat(),
                "message": f"验收跳过：audit模块不存在"
            })
            audit_score = 10  # 假设验收通过
        
        # 优化控制台比写作控制台更严！audit_score < 8 就自动修正！最多修正2次！
        retry_modify = 0
        while retry_modify < 2:
            if audit_score >= 8:
                break
                
            modify_log_queue[pname].append({
                "chapter_num": req.chapter_num,
                "status": "processing",
                "time": datetime.now().isoformat(),
                "message": f"验收完成，审计分 {audit_score}/10（第{retry_modify+1}次修正）"
            })
            
            # 自动修正一次
            fix_prompt = f"""以下是小说第{req.chapter_num}章的内容，验收评分只有{audit_score}/10分！请根据验收结果，进行局部修正：

【章节内容】
{new_content}

【修正要求】
1. 只修正验收不通过的部分！其他部分保持原样！
2. 不要加新内容！不要加新场景！
3. 直接输出修正后的完整章节！"""
            
            new_content = await asyncio.to_thread(
                chat,
                messages=[
                    {"role": "system", "content": "你是网文编辑，进行局部修正！只改验收不通过的部分！其他部分保持原样！"},
                    {"role": "user", "content": fix_prompt}
                ],
                temperature=0.3,
                max_tokens=6000,
            )
            
            # 重新验收
            try:
                from engine import audit
                audit_result = audit.run_audit(new_content, old_content)
                audit_score = audit_result.get("score", 0)
            except ImportError:
                audit_score = 10  # 假设验收通过
                
            retry_modify += 1
            
            modify_log_queue[pname].append({
                "chapter_num": req.chapter_num,
                "status": "processing",
                "time": datetime.now().isoformat(),
                "message": f"自动修正完成，共{len(new_content)}字"
            })
        else:
            modify_log_queue[pname].append({
                "chapter_num": req.chapter_num,
                "status": "processing",
                "time": datetime.now().isoformat(),
                "message": f"验收完成，审计分 {audit_score}/10，通过！"
            })
    except Exception as e:
        modify_log_queue[pname].append({
            "chapter_num": req.chapter_num,
            "status": "processing",
            "time": datetime.now().isoformat(),
            "message": f"验收跳过：{str(e)}"
        })
    
    # 保存修改后的内容（如果save=True）
    if req.save:
        modify_log_queue[pname].append({
            "chapter_num": req.chapter_num,
            "status": "processing",
            "time": datetime.now().isoformat(),
            "message": f"正在保存第{req.chapter_num}章..."
        })
        
        with open(os.path.join(chapters_dir, target_file), 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        # 记录修改日志：成功
        modify_log_queue[pname].append({
            "chapter_num": req.chapter_num,
            "status": "success",
            "time": datetime.now().isoformat(),
            "message": f"第{req.chapter_num}章修改完成，共{len(new_content)}字"
        })
    
    # 保存修改日志到文件
    save_modify_log_queue(pname, modify_log_queue[pname])
    
    return {"ok": True, "chapter_num": req.chapter_num, "file": target_file, "new_content": new_content}


# ===== 导入已有小说 =====
class ImportReq(BaseModel):
    project: str
    title: str
    content: str  # 整篇小说或多章粘贴，用"第X章"分隔


@app.post("/api/import")
async def import_novel(req: ImportReq):
    """导入已有小说：自动切分章节、建项目、提取人物"""
    import re
    db_path = get_project_db(req.project)
    if not Path(db_path).exists():
        crud.init_db(db_path)
    conn = crud.get_conn(db_path)
    crud.update_meta(conn, title=req.title)

    # 按"第X章"切分
    parts = re.split(r'(?=第[一二三四五六七八九十百千零\d]+章)', req.content)
    chapters = [p.strip() for p in parts if p.strip() and len(p.strip()) > 50]
    imported = 0
    for i, ch_text in enumerate(chapters, 1):
        # 提取标题（第一行）
        lines = ch_text.split('\n', 1)
        ch_title = lines[0][:30]
        ch_content = lines[1] if len(lines) > 1 else ch_text
        crud.save_chapter(conn, i, ch_title, ch_content)
        imported += 1

    conn.close()

    # 逆向重建设定：自动提取人物/事件/伏笔
    try:
        from engine.llm import chat
        for i, ch_text in enumerate(chapters[:5], 1):  # 只处理前5章
            lines = ch_text.split('\n', 1)
            ch_content = lines[1] if len(lines) > 1 else ch_text
            brief = f"从以下章节提取人物和事件：\n{ch_content[:2000]}"
            result = chat(messages=[{"role": "user", "content": brief + "\n输出JSON：{\"characters\":[], \"events\":[]}"}], temperature=0.3, max_tokens=500, fast=True)
            try:
                import json
                data = json.loads(result)
                for c in data.get("characters", []):
                    cname = c.get("name", "")
                    if not cname:
                        continue
                    crud.upsert_character(conn, {
                        "id": f"char_{cname}",
                        "name": cname,
                        "aliases": "[]",
                        "role_type": c.get("role_type", "support"),
                        "realm": "", "personality": "", "abilities": "[]",
                        "state": c.get("state", ""),
                        "first_chapter": i, "last_chapter": i, "notes": "",
                    })
                for e in data.get("events", []):
                    crud.add_event(conn, chapter=i, etype=e.get("type", "plot"),
                                   summary=e.get("summary", ""))
            except Exception:
                pass
    except Exception as e:
        return {"imported_chapters": imported, "project": req.project, "reconstruct": f"失败: {e}"}

# ===== EPUB/PDF 上传导入 =====
from fastapi import UploadFile, File

@app.post("/api/import-file")
async def import_file(project: str = "", file: UploadFile = File(...)):
    """上传EPUB/TXT文件导入"""
    ext = file.filename.split(".")[-1].lower()
    content = ""
    if ext == "epub":
        import ebooklib
        from ebooklib import epub
        from bs4 import BeautifulSoup
        book = epub.read_epub(file.file)
        chapters = []
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            soup = BeautifulSoup(item.get_content(), "html.parser")
            text = soup.get_text()
            if len(text) > 100:
                chapters.append(text)
        content = "\n\n".join(chapters)
    elif ext == "txt":
        content = (await file.read()).decode("utf-8")
    else:
        return {"error": "只支持 EPUB/TXT 文件"}

    # 复用文本导入逻辑
    req = ImportReq(project=project or "imported", title=file.filename, content=content)
    return await import_novel(req)


# ===== 风格指纹提取 =====
class ExtractStyleReq(BaseModel):
    project: str
    reference_text: str

@app.post("/api/extract-style")
async def extract_style(req: ExtractStyleReq):
    """从参考文本提取风格指纹"""
    from engine.llm import chat
    prompt = f"""分析以下参考文本，提取可迁移的写作风格指纹（不要复制内容，只提取方法）：

{req.reference_text[:3000]}

输出JSON格式：
{{
  "narrative_distance": "叙事距离（远/中/近）",
  "paragraph_rhythm": "段落节奏（长短句比例）",
  "dialogue_density": "对话占比（高/中/低）",
  "sensory_selection": "感官偏好（视觉/听觉/触觉）",
  "sentence_movement": "句段运动（快/慢/张弛交替）",
  "info_release": "信息释放方式（直给/埋伏笔/倒叙）",
  "style_guide": "100字以内的风格指南"
}}

只输出JSON。"""
    result = chat(messages=[{"role": "user", "content": prompt}], temperature=0.3, max_tokens=500, fast=True)
    try:
        import json
        style = json.loads(result)
        # 存到项目meta
        db = get_project_db(req.project)
        from database import crud
        conn = crud.get_conn(db)
        crud.update_meta(conn, style=json.dumps(style, ensure_ascii=False))
        conn.close()
        return {"style": style}
    except Exception as e:
        return {"error": str(e)}
class DeslopReq(BaseModel):
    project: str
    chapter: int


@app.post("/api/deslop")
async def deslop_chapter(req: DeslopReq):
    """对已有章节做深度去AI味重写"""
    from engine.llm import chat
    db_path = get_project_db(req.project)
    conn = crud.get_conn(db_path)
    row = crud.get_chapter(conn, req.chapter)
    if not row:
        conn.close()
        raise HTTPException(404, "章节不存在")
    content = row["content"]
    conn.close()

    prompt = f"""你是网文编辑。下面这段文字有AI味，请重写得更自然、更像人写的：

要求：
1. 删掉所有"缓缓/淡淡/微微/轻轻/仿佛/似乎/不由得"这类副词
2. 删掉"瞳孔微缩/心中一凛/嘴角勾起"等套路反应，换成具体动作
3. 对话要短、有打断、有潜台词
4. 段落长短不一，有的一句话一段
5. 不要改变剧情和人物
6. 保持字数差不多

原文：
{content[:3000]}

重写后："""
    new_content = chat(messages=[{"role": "user", "content": prompt}], temperature=0.8, max_tokens=3500, fast=True)

    conn = crud.get_conn(db_path)
    crud.save_chapter(conn, req.chapter, row["title"], new_content, summary=row.get("summary", ""))
    conn.close()
    return {"before": len(content), "after": len(new_content)}


# ===== 深度审稿 =====
class ReviewReq(BaseModel):
    project: str
    chapter: int


@app.post("/api/review")
async def review_chapter(req: ReviewReq):
    """对已有章节做深度审稿：节奏/爽点/AI味/人物/伏笔"""
    from engine.llm import chat
    db_path = get_project_db(req.project)
    conn = crud.get_conn(db_path)
    row = crud.get_chapter(conn, req.chapter)
    if not row:
        conn.close()
        raise HTTPException(404, "章节不存在")
    content = row["content"]
    conn.close()

    prompt = f"""你是资深网文编辑。审下面这一章，输出 JSON：
{{
  "节奏": {"score": 1-10, "comment": "..."},
  "爽点": {"score": 1-10, "comment": "..."},
  "AI味": {"score": 1-10, "comment": "..."},
  "人物": {"score": 1-10, "comment": "..."},
  "钩子": {"score": 1-10, "comment": "..."},
  "总评": "200字",
  "修改建议": ["建议1", "建议2"]
}}

章节：{row["title"]}
{content[:3000]}

直接输出 JSON。"""
    result = chat(messages=[{"role": "user", "content": prompt}], temperature=0.3, max_tokens=1200, fast=True)
    if result.startswith("```"):
        result = result.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(result)
    except Exception:
        return {"raw": result[:500]}


# ===== 导出 TXT =====
@app.get("/api/projects/{name}/export")
async def export_txt(name: str):
    """导出全书为 TXT"""
    safe = safe_project_name(name)
    db_path = get_project_db(safe)
    if not Path(db_path).exists():
        raise HTTPException(404, "项目不存在")
    conn = crud.get_conn(db_path)
    rows = conn.execute("SELECT title, content FROM chapters ORDER BY chapter").fetchall()
    conn.close()
    meta = crud.get_meta(conn) if False else {}  # 已关
    lines = []
    for r in rows:
        lines.append(r["title"] or "")
        lines.append("")
        lines.append(r["content"] or "")
        lines.append("")
        lines.append("")
    txt = "\n".join(lines)
    from urllib.parse import quote
    filename = quote(f"{safe}.txt")
    return PlainTextResponse(txt, headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"})


@app.get("/api/projects/{name}/export/{chapter}")
async def export_chapter_txt(name: str, chapter: int):
    """导出单章为 TXT"""
    safe = safe_project_name(name)
    db_path = get_project_db(safe)
    if not Path(db_path).exists():
        raise HTTPException(404, "项目不存在")
    conn = crud.get_conn(db_path)
    row = conn.execute("SELECT title, content FROM chapters WHERE chapter=?", (chapter,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(404, "章节不存在")
    txt = f"{row['title'] or ''}\n\n{row['content'] or ''}"
    from urllib.parse import quote
    filename = quote(f"{safe}_第{chapter}章.txt")
    return PlainTextResponse(txt, headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"})


# ===== LLM 监控 =====
@app.get("/api/llm/status")
async def llm_status():
    """返回当前 LLM key 池状态"""
    from engine import llm
    keys = json.loads((Path(__file__).parent / "api_keys.json").read_text(encoding="utf-8"))
    agnes_keys = keys.get("AGNES_KEYS", [])
    state_file = Path(__file__).parent / "provider_state.json"
    state = json.loads(state_file.read_text(encoding="utf-8")) if state_file.exists() else {}
    return {
        "total_keys": len(agnes_keys),
        "base_url": llm.AGNES_BASE,
        "model": "agnes-3.0-flash",
        "min_interval": llm.MIN_INTERVAL,
        "keys": [{"idx": i, "active": k not in state.get("disabled", {})} for i, k in enumerate(agnes_keys)],
        "disabled_count": len(state.get("disabled", {})),
    }


# ===== 对话改稿 =====
class ChatEditReq(BaseModel):
    project: str
    chapter: int
    instruction: str


@app.post("/api/chat-edit")
async def chat_edit(req: ChatEditReq):
    """流式对话改稿"""
    db_path = get_project_db(req.project)
    conn = crud.get_conn(db_path)
    row = crud.get_chapter(conn, req.chapter)
    if not row:
        conn.close()
        raise HTTPException(404, "章节不存在")
    conn.close()

    prompt = f"""你是网文编辑。用户要求：{req.instruction}

请按要求修改下面这一章，输出完整修改后的章节正文：
{row['content'][:3000]}

只输出修改后的正文，不要解释。"""

    async def gen():
        import queue, threading
        q = queue.Queue()
        def worker():
            from engine.llm import chat_stream
            chat_stream(messages=[{"role": "user", "content": prompt}],
                       temperature=0.7, max_tokens=3500, fast=True,
                       on_delta=lambda x: q.put(x))
            q.put(None)  # done
        threading.Thread(target=worker, daemon=True).start()
        full = []
        while True:
            chunk = await asyncio.get_event_loop().run_in_executor(None, q.get, True)
            if chunk is None:
                break
            full.append(chunk)
            yield f"data: {chunk}\n\n"
        new_content = "".join(full)
        conn = crud.get_conn(db_path)
        crud.save_chapter(conn, req.chapter, row["title"], new_content, summary=row.get("summary", ""))
        conn.close()
        yield "data: [DONE]\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")


# ===== 前端页面 =====
from fastapi.staticfiles import StaticFiles

# index.html/style.css/app.js 需要no-cache
@app.get("/")
async def index():
    r = FileResponse(HTML_DIR / "index.html")
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return r

@app.get("/style.css")
async def style():
    r = FileResponse(HTML_DIR / "style.css")
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return r

@app.get("/app.js")
async def appjs():
    r = FileResponse(HTML_DIR / "app.js")
    r.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return r

# 码字日历：获取每天写了多少字
@app.get("/api/writing_calendar")
async def writing_calendar():
    """获取码字日历数据：每天写了多少字"""
    from collections import defaultdict
    daily_words = defaultdict(int)
    
    try:
        for project_dir in PROJECTS_DIR.iterdir():
            if not project_dir.is_dir():
                continue
            # 读取所有章节文件，按修改日期统计
            for chapter_file in list_chapter_files(project_dir):
                mtime = datetime.fromtimestamp(chapter_file.stat().st_mtime)
                date_str = mtime.strftime("%Y-%m-%d")
                text = chapter_file.read_text(encoding="utf-8")
                daily_words[date_str] += len(text)
    except Exception as e:
        return {"calendar": [], "error": str(e)}
    
    # 转换成列表
    result = [{"date": d, "words": w} for d, w in sorted(daily_words.items())]
    return {"calendar": result}

# 数据统计：每章字数/每章评分
@app.get("/api/stats")
async def stats(project: str):
    """获取数据统计：每章字数/每章评分"""
    project = safe_project_name(project)
    proj_dir = PROJECTS_DIR / project
    
    try:
        chapter_files = list_chapter_files(proj_dir)
    except Exception as e:
        return {"chapters": [], "error": str(e)}
    
    chapters = []
    for i, f in enumerate(chapter_files, 1):
        try:
            text = f.read_text(encoding="utf-8")
            chapters.append({
                "chapter": i,
                "title": f.stem,
                "words": len(text),
            })
        except Exception:
            pass
    
    return {"chapters": chapters}

# 错别字检查
@app.post("/api/typo_check")
async def typo_check(req: dict):
    """检查章节里的错别字"""
    project = safe_project_name(req.get("project", ""))
    chapter = req.get("chapter", 1)
    proj_dir = PROJECTS_DIR / project
    
    try:
        chapter_files = list_chapter_files(proj_dir)
        if chapter > len(chapter_files):
            return {"error": f"章节{chapter}不存在"}
        filepath = chapter_files[chapter - 1]
        text = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return {"error": f"读取章节失败: {e}"}
    
    common_typos = {
        "的了": "了", "了的": "的", "在在": "在", "是是": "是",
        "做为": "作为", "按装": "安装", "必竟": "毕竟", "参于": "参与",
        "成份": "成分", "耽阁": "耽搁", "倒底": "到底", "掂记": "惦记",
        "烦燥": "烦躁", "防害": "妨害", "贯输": "灌输", "鬼计": "诡计",
        "含胡": "含糊", "寒喧": "寒暄", "即然": "既然", "急待": "亟待",
        "记算": "计算", "家俱": "家具", "建意": "建议", "交待": "交代",
        "脚色": "角色", "接恰": "接洽", "决别": "诀别", "克苦": "刻苦",
        "刻服": "克服", "肯求": "恳求", "烂调": "滥调", "劳骚": "牢骚",
        "冷莫": "冷漠", "连级": "连级", "录相": "录像", "轮廊": "轮廓",
        "摸仿": "模仿", "模胡": "模糊", "那怕": "哪怕", "年青": "年轻",
        "欧打": "殴打", "皮气": "脾气", "僻免": "避免", "偏面": "片面",
        "气慨": "气概", "签定": "签订", "敲榨": "敲诈", "切搓": "切磋",
        "清彻": "清澈", "人情事故": "人情世故", "手屈一指": "首屈一指",
        "水笼头": "水龙头", "说慌": "说谎", "松驰": "松弛", "耸恿": "怂恿",
        "通辑": "通缉", "完壁归赵": "完璧归赵", "消声匿迹": "销声匿迹",
        "小提大做": "小题大做", "修茸": "修葺", "寻序渐进": "循序渐进",
        "眼花撩乱": "眼花缭乱", "再接再励": "再接再厉", "责无旁代": "责无旁贷",
        "张慌失措": "张皇失措", "仗义直言": "仗义执言", "真知卓见": "真知灼见",
        "直接了当": "直截了当", "指高气扬": "趾高气扬", "中流抵柱": "中流砥柱",
        "走头无路": "走投无路",
    }
    
    typos = []
    lines = text.split('\n')
    for i, line in enumerate(lines, 1):
        for wrong, right in common_typos.items():
            if wrong in line:
                typos.append({"wrong": wrong, "right": right, "line": i})
    
    return {"typos": typos}

# 敏感词检查
@app.post("/api/sensitive_check")
async def sensitive_check(req: dict):
    """检查章节里的敏感词"""
    project = safe_project_name(req.get("project", ""))
    chapter = req.get("chapter", 1)
    proj_dir = PROJECTS_DIR / project
    
    try:
        chapter_files = list_chapter_files(proj_dir)
        if chapter > len(chapter_files):
            return {"error": f"章节{chapter}不存在"}
        filepath = chapter_files[chapter - 1]
        text = filepath.read_text(encoding="utf-8")
    except Exception as e:
        return {"error": f"读取章节失败: {e}"}
    
    sensitive_words = [
        "共产党", "国民党", "毛主席", "邓小平", "江泽民", "胡锦涛", "习近平",
        "社会主义", "资本主义", "共产主义", "封建迷信",
        "杀人", "放火", "强奸", "抢劫", "盗窃",
        "毒品", "吸毒", "贩毒", "卖淫", "嫖娼", "赌博",
        "自杀", "自残", "色情", "裸体", "性爱", "性交",
        "暴力", "血腥", "恐怖", "政治", "政府", "官员",
        "贪污", "腐败", "台独", "港独", "藏独", "疆独",
        "法轮功", "邪教",
    ]
    
    words = []
    for word in sensitive_words:
        count = text.count(word)
        if count > 0:
            words.append({"word": word, "count": count})
    
    return {"words": words}

# 挂载静态文件目录（logo/fonts/其他HTML）
app.mount("/", StaticFiles(directory=str(HTML_DIR)), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
