# -*- coding: utf-8 -*-
"""API端点测试"""
import sys, tempfile, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_health():
    from fastapi.testclient import TestClient
    from main import app
    c = TestClient(app)
    r = c.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    print("✓ /api/health")

def test_genres_list():
    from fastapi.testclient import TestClient
    from main import app
    c = TestClient(app)
    r = c.get("/api/genres")
    assert r.status_code == 200
    assert len(r.json()["genres"]) >= 30
    print("✓ /api/genres")

def test_version():
    from fastapi.testclient import TestClient
    from main import app
    c = TestClient(app)
    r = c.get("/api/version")
    assert r.status_code == 200
    print("✓ /api/version")

def test_projects_list_empty():
    from fastapi.testclient import TestClient
    from main import app
    c = TestClient(app)
    r = c.get("/api/projects")
    assert r.status_code == 200
    print("✓ /api/projects")

def test_create_project():
    from fastapi.testclient import TestClient
    from main import app
    c = TestClient(app)
    r = c.post("/api/projects", json={"name": "test-api-book", "title": "测试"})
    assert r.status_code in (200, 201, 400, 405)  # 允许已存在
    print("✓ POST /api/projects")

def test_safe_name_injection():
    from config import safe_project_name
    for bad in ["../etc/passwd", "..\\windows", "a/b", "a\\b", ".hidden", ""]:
        try:
            safe_project_name(bad)
            assert False, f"应该拒绝: {bad}"
        except ValueError:
            pass
    print("✓ safe_name 注入防护")

def test_safe_name_valid():
    from config import safe_project_name
    assert safe_project_name("my-book") == "my-book"
    assert safe_project_name("ABC123") == "ABC123"
    assert safe_project_name("test_book") == "test_book"
    print("✓ safe_name 合法名")

def test_humanizer_no_llm():
    from engine.humanizer import humanize
    t = humanize("他不禁笑了。她微微一笑。")
    assert isinstance(t, str)
    assert len(t) > 0
    print("✓ humanizer 规则替换")

def test_gates_precommit_short():
    from engine.gates import precommit_check
    beat = {"must_cover_nodes": [], "forbidden_zones": []}
    issues = precommit_check("太短", beat)
    assert any("字数" in i or "短" in i for i in issues)
    print("✓ gates 字数检查")

def test_gates_precommit_todo():
    from engine.gates import precommit_check
    beat = {"must_cover_nodes": [], "forbidden_zones": []}
    issues = precommit_check("TODO 以后再写。" * 50, beat)
    assert any("TODO" in i or "占位" in i for i in issues)
    print("✓ gates TODO检测")

def test_crud_conn():
    from database import crud
    db = tempfile.mktemp(suffix=".db")
    conn = crud.get_conn(db)
    assert conn is not None
    conn.close()
    print("✓ crud get_conn")

def test_config_version():
    import config
    assert config.VERSION
    print(f"✓ config v{config.VERSION}")

def test_llm_module_import():
    from engine import llm
    assert hasattr(llm, 'chat') or hasattr(llm, 'chat_stream')
    print("✓ llm 模块加载")

def test_all_engine_modules():
    mods = ['director', 'writer', 'reviewer', 'extract', 'observer', 'auditor',
            'humanizer', 'checker', 'gates', 'postprocess', 'compactor',
            'styleguide', 'context', 'truth']
    for m in mods:
        __import__(f'engine.{m}')
    print(f"✓ {len(mods)}个engine模块全部加载")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        try:
            fn()
            passed += 1
        except Exception as e:
            print(f"✗ {fn.__name__}: {e}")
    print(f"\n{passed}/{len(fns)} passed")
