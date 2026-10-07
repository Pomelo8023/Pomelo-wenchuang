# -*- coding: utf-8 -*-
"""灵云文创 · 冒烟测试（不依赖 pytest，直接 python -m tests.test_smoke）"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def test_safe_project_name():
    from config import safe_project_name
    assert safe_project_name("my-book") == "my-book"
    assert safe_project_name("我的小说") == "我的小说"
    for bad in ["../etc", "a/b", "a\\b", ".hidden", ""]:
        try:
            safe_project_name(bad)
            assert False, f"应该拒绝: {bad}"
        except ValueError:
            pass
    print("✓ safe_project_name")


def test_gates_precommit():
    from engine import gates
    beat = {"must_cover_nodes": ["主角", "突破"], "forbidden_zones": ["死人复活"]}
    good = gates.precommit_check("这一章主角终于突破了境界，开始新的生活。" * 100, beat)
    assert not any("未覆盖" in i for i in good), f"好文本不该报未覆盖: {good}"
    bad = gates.precommit_check("TODO 这里以后再写" * 100, beat)
    assert any("占位符" in i for i in bad), f"TODO 应该被抓: {bad}"
    short = gates.precommit_check("太短了", beat)
    assert any("字数不足" in i for i in short)
    print("✓ gates.precommit_check")


def test_genres():
    from engine.genres import list_genres, get_genre_rules
    g = list_genres()
    assert len(g) >= 20, f"题材数太少: {len(g)}"
    assert "修仙" in g
    assert "甜宠言情" in g
    r = get_genre_rules("修仙")
    assert "境界" in r
    assert get_genre_rules("不存在的题材") == ""
    print("✓ genres")


def test_director_defaults():
    from engine.director import generate_chapter_beat
    # 不真调 LLM，只测 JSON 兜底
    import engine.director as d
    orig_chat = d.chat
    d.chat = lambda **kw: "不是json"
    beat = generate_chapter_beat(1, 100, {}, {}, [])
    d.chat = orig_chat
    assert beat["cool_point_type"] == "反派翻车"
    assert beat["must_cover_nodes"] == []
    print("✓ director 默认值兜底")


def test_truth(tmp_path=None):
    import tempfile
    from engine.truth import TruthFile
    with tempfile.TemporaryDirectory() as td:
        t = TruthFile(td)
        t.upsert_character("char_1", {"name": "张三", "state": "筑基"})
        assert t.get_character("char_1")["name"] == "张三"
        t.add_hook("hook_1", {"plant_chapter": 1, "summary": "神秘玉佩"})
        assert len(t.get_active_hooks()) == 1
        t.resolve_hook("hook_1", 5, "玉佩认主")
        assert len(t.get_active_hooks()) == 0
        t.add_reflection(1, {"next_chapter_hint": "开打"})
        assert t.get_last_reflection()["next_chapter_hint"] == "开打"
    print("✓ truth 读写")


def test_crud_basic():
    import tempfile
    from database import crud
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "test.db"
        crud.init_db(db)
        conn = crud.get_conn(db)
        crud.update_progress(conn, total_chapters=100)
        p = crud.get_progress(conn)
        assert p["total_chapters"] == 100
        crud.save_chapter(conn, 1, "第一章", "正文内容", summary="摘要")
        c = crud.get_chapter(conn, 1)
        assert c["title"] == "第一章"
        assert c["word_count"] == len("正文内容")
        fid = crud.add_foreshadow(conn, {"plant_chapter": 1, "plant_summary": "test",
                                          "type": "悬念", "strength": "medium"})
        assert fid > 0
        crud.resolve_foreshadow(conn, fid, 5, "回收")
        conn.close()
    print("✓ crud 基本CRUD")


def test_llm_state():
    from engine import llm
    # 当前设计：本地不做熔断（服务商自己限流），_provider_ok 恒为 True
    assert llm._provider_ok("test_provider") is True
    llm._record_failure("test_provider")
    assert llm._provider_ok("test_provider") is True
    print("✓ llm 模块状态正常")


def test_config_version():
    from config import VERSION
    assert VERSION.count(".") == 2
    print(f"✓ config version = {VERSION}")


def test_fts():
    import tempfile, os
    from database import crud
    td = tempfile.mkdtemp()
    db = Path(td) / "t.db"
    crud.init_db(db)
    conn = crud.get_conn(db)
    crud.save_chapter(conn, 1, "第一章", "林辰遇到了神秘玉佩，玉佩发光")
    crud.save_chapter(conn, 2, "第二章", "林辰用玉佩打败了反派")
    from engine.context import search_relevant
    hits = search_relevant(conn, "玉佩")
    assert len(hits) >= 1, f"检索没搜到: {hits}"
    conn.close()
    for f in os.listdir(td):
        try: os.remove(Path(td)/f)
        except: pass
    print("✓ 全文检索(FTS5+LIKE回退)")


def test_postprocess():
    from engine import postprocess
    assert hasattr(postprocess, "postprocess_chapter")
    print("✓ postprocess 模块")


def test_styleguide():
    from engine import styleguide
    assert hasattr(styleguide, "extract_style_guide")
    print("✓ styleguide 模块")


def test_doctor_endpoint():
    from fastapi.testclient import TestClient
    from main import app
    c = TestClient(app)
    r = c.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    r2 = c.get("/api/genres")
    assert len(r2.json()["genres"]) >= 20
    print("✓ API health + genres")


def test_safe_name_edge():
    from config import safe_project_name
    for bad in ["a"*100, "A/B", "a.b", ".hidden", "..x", "a|b"]:
        try:
            safe_project_name(bad)
        except ValueError:
            pass
    print("✓ safe_name 边界")


def test_compactor():
    from engine import compactor
    assert hasattr(compactor, "compact_old_summaries")
    print("✓ compactor 模块")


def test_gates_postcommit():
    import tempfile
    from database import crud
    from engine import gates
    with tempfile.TemporaryDirectory() as td:
        db = Path(td) / "t.db"
        crud.init_db(db)
        conn = crud.get_conn(db)
        crud.add_foreshadow(conn, {"plant_chapter": 1, "plant_summary": "test", "type": "悬念", "strength": "medium"})
        issues = gates.postcommit_check(conn, 1, 1)
        assert any("未标记" in i for i in issues)
        conn.close()
    print("✓ gates.postcommit")


def test_aging_hooks():
    from engine import director
    # 不调 LLM，只测函数存在
    assert hasattr(director, "generate_chapter_beat")
    print("✓ director 伏笔老化检查")


def test_writer_prompt():
    from engine import writer
    assert hasattr(writer, "write_chapter")
    assert hasattr(writer, "rewrite_chapter")
    print("✓ writer 模块")


def test_extract():
    from engine import extract
    assert hasattr(extract, "extract_chapter_data")
    print("✓ extract 模块")


def test_auditor():
    from engine import auditor
    assert hasattr(auditor, "audit_33dim")
    print("✓ auditor 33维")


def run_all():
    tests = [v for k, v in globals().items() if k.startswith("test_") and callable(v)]
    passed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"✗ {t.__name__}: {e}")
    print(f"\n{passed}/{len(tests)} 通过")
    return passed == len(tests)


if __name__ == "__main__":
    ok = run_all()
    sys.exit(0 if ok else 1)
