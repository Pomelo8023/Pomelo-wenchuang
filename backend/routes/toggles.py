# -*- coding: utf-8 -*-
"""引擎开关路由（从 main.py 拆出）"""
import json
from fastapi import APIRouter
from pydantic import BaseModel

from config import PROJECTS_DIR, safe_project_name

router = APIRouter(prefix="/api/projects", tags=["toggles"])


class ToggleRequest(BaseModel):
    project: str
    key: str
    value: object


@router.get("/{name}/toggles")
async def get_toggles_api(name: str):
    name = safe_project_name(name)
    canon_path = PROJECTS_DIR / name / "story" / "state" / "canon.json"
    canon = json.loads(canon_path.read_text(encoding="utf-8")) if canon_path.exists() else {}
    from engine.settings import get_toggles
    return get_toggles(canon)


@router.post("/{name}/toggles")
async def set_toggle_api(req: ToggleRequest):
    name = safe_project_name(req.project)
    canon_path = PROJECTS_DIR / name / "story" / "state" / "canon.json"
    canon = json.loads(canon_path.read_text(encoding="utf-8")) if canon_path.exists() else {}
    from engine.settings import set_toggle, get_toggles
    canon = set_toggle(canon, req.key, req.value)
    canon_path.write_text(json.dumps(canon, ensure_ascii=False, indent=2), encoding="utf-8")
    return get_toggles(canon)
