"""SQLite 持久化：保存每次面试的完整结果，供管理员面板查询。"""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from .session import RunResult

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def default_db_path() -> Path:
    return PROJECT_ROOT / "data" / "personacore.db"


class Store:
    def __init__(self, db_path: str | None = None):
        self.db_path = str(db_path or default_db_path())
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS interviews (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT UNIQUE NOT NULL,
                        run_id TEXT,
                        started_at TEXT,
                        model TEXT,
                        composite REAL,
                        decision TEXT,
                        dimensions_json TEXT,
                        report_md TEXT,
                        full_json TEXT,
                        created_at TEXT
                    )
                    """
                )
                conn.commit()
            finally:
                conn.close()

    def save(self, session_id: str, result: RunResult) -> None:
        """保存一次面试结果（幂等：同一 session 只存一次）。"""
        d = result.to_dict()
        verdicts = d.get("verdicts", [])
        dims = [
            {"name": v.get("name"), "score": v.get("score"), "passed": v.get("passed")}
            for v in verdicts
        ]
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO interviews
                    (session_id, run_id, started_at, model, composite, decision,
                     dimensions_json, report_md, full_json, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', 'localtime'))
                    """,
                    (
                        session_id,
                        d.get("run_id"),
                        d.get("started_at"),
                        d.get("model"),
                        d.get("composite"),
                        d.get("decision"),
                        json.dumps(dims, ensure_ascii=False),
                        result.full_markdown(),
                        json.dumps(d, ensure_ascii=False),
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def list(self) -> List[Dict[str, Any]]:
        """候选人列表（不含完整报告）。"""
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT id, started_at, model, composite, decision, dimensions_json "
                    "FROM interviews ORDER BY id DESC"
                ).fetchall()
            finally:
                conn.close()
        out: List[Dict[str, Any]] = []
        for r in rows:
            item = dict(r)
            item["dimensions"] = json.loads(item.pop("dimensions_json") or "[]")
            out.append(item)
        return out

    def get(self, record_id: int) -> Optional[Dict[str, Any]]:
        """单条完整记录（含报告 markdown 与结构化数据）。"""
        with self._lock:
            conn = self._connect()
            try:
                row = conn.execute(
                    "SELECT * FROM interviews WHERE id = ?", (record_id,)
                ).fetchone()
            finally:
                conn.close()
        if row is None:
            return None
        item = dict(row)
        item["full"] = json.loads(item["full_json"] or "{}")
        item.pop("full_json", None)
        return item
