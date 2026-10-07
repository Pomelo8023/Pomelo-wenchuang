"""灵云文创 · 配置加载"""
import os
import re
import yaml
from pathlib import Path

ROOT = Path(__file__).parent.parent
CONFIG_PATH = ROOT / "config.yaml"
PROJECTS_DIR = ROOT / "projects"

VERSION = "1.0.0"


def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def safe_project_name(name: str) -> str:
    """项目名安全校验：只允许字母数字下划线短横线中文，防路径遍历"""
    name = name.strip()
    if not name:
        raise ValueError("项目名不能为空")
    # Windows文件名非法字符：\ / : * ? " < > |
    if ".." in name or "/" in name or "\\" in name or name.startswith("."):
        raise ValueError("项目名非法")
    # 把Windows非法字符替换成安全字符
    for ch in [":", "：", "*", "?", '"', "<", ">", "|"]:
        name = name.replace(ch, "-")
    if not re.match(r'^[\w\u4e00-\u9fa5\-]+$', name):
        raise ValueError("项目名只能含中文/字母/数字/下划线/短横线")
    return name


def get_project_db(project_name: str) -> Path:
    pname = safe_project_name(project_name)
    p = PROJECTS_DIR / pname
    p.mkdir(parents=True, exist_ok=True)
    return p / "story.db"


def get_project_dir(project_name: str) -> Path:
    pname = safe_project_name(project_name)
    p = PROJECTS_DIR / pname
    p.mkdir(parents=True, exist_ok=True)
    (p / "正文").mkdir(exist_ok=True)
    (p / "设定集").mkdir(exist_ok=True)
    return p
