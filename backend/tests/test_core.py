# -*- coding: utf-8 -*-
"""核心模块单元测试（只验证能import）"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_humanizer(): from engine import humanizer; print("✓ humanizer")
def test_compactor(): from engine import compactor; print("✓ compactor")
def test_auditor(): from engine import auditor; print("✓ auditor")
def test_extract(): from engine import extract; print("✓ extract")
def test_director(): from engine import director; print("✓ director")
def test_writer(): from engine import writer; print("✓ writer")
def test_postprocess(): from engine import postprocess; print("✓ postprocess")
def test_observer(): from engine import observer; print("✓ observer")
def test_reviewer(): from engine import reviewer; print("✓ reviewer")
def test_checker(): from engine import checker; print("✓ checker")
def test_gates(): from engine import gates; print("✓ gates")
def test_truth(): from engine import truth; print("✓ truth")
def test_crud(): from database import crud; print("✓ crud")
def test_genres(): from engine.genres import list_genres; g=list_genres(); assert len(g)>=30; print(f"✓ genres({len(g)})")
def test_config(): import config; assert hasattr(config,'VERSION'); print(f"✓ config v{config.VERSION}")
def test_styleguide(): from engine import styleguide; print("✓ styleguide")
def test_llm(): from engine import llm; print("✓ llm")
def test_context(): from engine import context; print("✓ context")
def test_safe_name(): from config import safe_project_name; assert safe_project_name("my-book")=="my-book"; print("✓ safe_name")


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = sum(1 for fn in fns if (fn() or True))
    print(f"\n{passed}/{len(fns)} passed")
