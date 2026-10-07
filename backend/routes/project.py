# -*- coding: utf-8 -*-
"""项目只读查询路由（从 main.py 拆出）"""
import os
import re
import json
from fastapi import APIRouter
from pydantic import BaseModel

from config import get_project_db, get_project_dir, PROJECTS_DIR, safe_project_name
from database import crud

router = APIRouter(prefix="/api/projects", tags=["project"])


# ===== 章节 =====
@router.get("/{name}/chapters")
async def list_chapters(name: str):
    pname = safe_project_name(name)
    proj_dir = str(get_project_dir(pname))
    chapters_dir = os.path.join(proj_dir, "正文")
    chapters = []
    if os.path.exists(chapters_dir):
        files = [f for f in os.listdir(chapters_dir) if f.endswith('.md')]
        for f in files:
            m = re.match(r'第(\d+)章\s*(.*)', f.replace('.md', ''))
            if m:
                ch_num = int(m.group(1))
                title = m.group(2).strip() or f.replace('.md', '')
                chapters.append({"num": ch_num, "title": title})
        chapters.sort(key=lambda x: x["num"])
    if chapters:
        return {"chapters": chapters}
    conn = crud.get_conn(get_project_db(name))
    chs = crud.list_chapters(conn)
    conn.close()
    return chs


@router.get("/{name}/chapters/{ch}")
async def get_chapter(name: str, ch: int):
    conn = crud.get_conn(get_project_db(name))
    c = crud.get_chapter(conn, ch)
    conn.close()
    return c or {}


class ChapterUpdate(BaseModel):
    title: str = ""
    content: str = ""


@router.put("/{name}/chapters/{ch}")
async def update_chapter(name: str, ch: int, req: ChapterUpdate):
    conn = crud.get_conn(get_project_db(name))
    old = crud.get_chapter(conn, ch)
    if not old:
        conn.close()
        return {"error": "章节不存在"}
    crud.save_chapter(conn, ch,
                      title=req.title or old.get("title", ""),
                      content=req.content or old.get("content", ""),
                      summary=old.get("summary", ""))
    conn.close()
    proj_dir = get_project_dir(name)
    (proj_dir / "正文" / f"第{ch:04d}章 {req.title or old.get('title','')}.md").write_text(
        f"# {req.title or old.get('title','')}\n\n{req.content}", encoding="utf-8")
    return {"status": "saved"}


@router.get("/{name}/emotion-arc")
async def get_emotion_arc(name: str):
    from engine.truth import TruthFile
    truth = TruthFile(get_project_dir(name))
    return {"arc": truth.get_emotional_arc()}


# ===== 人物 =====
@router.get("/{name}/characters")
async def list_characters(name: str):
    conn = crud.get_conn(get_project_db(name))
    chars = crud.list_characters(conn)
    conn.close()
    return chars


@router.get("/{name}/characters/{cid}")
async def get_character(name: str, cid: str):
    conn = crud.get_conn(get_project_db(name))
    c = crud.get_character(conn, cid)
    changes = crud.list_state_changes(conn, entity_id=cid)
    conn.close()
    return {**(c or {}), "state_changes": changes}


# ===== 关系 =====
@router.get("/{name}/relationships")
async def list_relationships(name: str):
    conn = crud.get_conn(get_project_db(name))
    rels = crud.list_relationships(conn)
    conn.close()
    return rels


# ===== 状态变化 =====
@router.get("/{name}/state-changes")
async def list_state_changes(name: str):
    conn = crud.get_conn(get_project_db(name))
    changes = crud.list_state_changes(conn)
    conn.close()
    return changes[:50]


# ===== 伏笔 =====
@router.get("/{name}/foreshadows")
async def list_foreshadows(name: str):
    conn = crud.get_conn(get_project_db(name))
    fs = crud.list_all_foreshadows(conn)
    conn.close()
    return fs


# ===== 事件 =====
@router.get("/{name}/events")
async def list_events(name: str):
    conn = crud.get_conn(get_project_db(name))
    events = crud.list_events(conn)
    conn.close()
    return events


# ===== 日志 =====
@router.get("/{name}/logs")
async def list_logs(name: str):
    conn = crud.get_conn(get_project_db(name))
    logs = crud.list_logs(conn, limit=50)
    conn.close()
    return logs


# ===== 设定 =====
def _get_canon_path(name: str):
    pname = safe_project_name(name)
    return PROJECTS_DIR / pname / "story" / "state" / "canon.json"


@router.get("/{name}/settings")
async def get_settings(name: str):
    canon_path = _get_canon_path(name)
    if canon_path.exists():
        canon = json.loads(canon_path.read_text(encoding="utf-8"))
        if isinstance(canon.get("outline"), dict):
            phases = canon["outline"].get("phases", [])
            outline_text = ""
            for i, p in enumerate(phases):
                outline_text += f"第{i+1}阶段（{p.get('chapters','')}）：{p.get('summary','')}\n"
            canon["outline"] = outline_text.strip()
        return canon
    return {}


@router.get("/{name}/timeline")
async def get_timeline(name: str):
    pname = safe_project_name(name)
    timeline_path = PROJECTS_DIR / pname / "story" / "state" / "timeline.json"
    if timeline_path.exists():
        return json.loads(timeline_path.read_text(encoding="utf-8"))
    return []
