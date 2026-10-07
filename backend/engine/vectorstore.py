# -*- coding: utf-8 -*-
"""向量RAG：章节语义检索"""
import chromadb
from pathlib import Path
from chromadb.config import Settings

_client = None
_collections = {}

# 绝对路径：避免从不同目录启动后端时 chroma_db 写到不同地方
_CHROMA_DIR = str(Path(__file__).resolve().parent.parent / "chroma_db")


def get_collection(project: str):
    """获取项目的向量集合"""
    global _client
    if _client is None:
        _client = chromadb.Client(Settings(anonymized_telemetry=False, is_persistent=True, persist_directory=_CHROMA_DIR))
    if project not in _collections:
        _collections[project] = _client.get_or_create_collection(name=f"novel_{project}")
    return _collections[project]


def add_chapter(project: str, chapter: int, title: str, content: str):
    """添加章节到向量库"""
    col = get_collection(project)
    col.upsert(
        ids=[f"ch_{chapter}"],
        documents=[f"第{chapter}章 {title}\n{content[:500]}"],
        metadatas=[{"chapter": chapter, "title": title}]
    )


def search(project: str, query: str, n_results: int = 3):
    """语义搜索相关章节"""
    col = get_collection(project)
    results = col.query(query_texts=[query], n_results=n_results)
    if results["documents"] and results["documents"][0]:
        return [{"chapter": results["metadatas"][0][i]["chapter"],
                 "title": results["metadatas"][0][i]["title"],
                 "content": results["documents"][0][i]}
                for i in range(len(results["documents"][0]))]
    return []
