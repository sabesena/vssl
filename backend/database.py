import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id          TEXT PRIMARY KEY,
                    title       TEXT NOT NULL DEFAULT 'New Conversation',
                    model       TEXT NOT NULL DEFAULT 'mistral:7b-instruct',
                    system_prompt TEXT,
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id              TEXT PRIMARY KEY,
                    conversation_id TEXT NOT NULL,
                    role            TEXT NOT NULL,
                    content         TEXT NOT NULL,
                    metadata        TEXT,
                    created_at      TEXT NOT NULL,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_messages_conv
                    ON messages(conversation_id, created_at);
            """)

    # ── conversations ──────────────────────────────────────────────────────────

    def create_conversation(
        self, model: str = "mistral:7b-instruct", system_prompt: Optional[str] = None
    ) -> dict:
        conv_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO conversations (id, model, system_prompt, created_at, updated_at) VALUES (?,?,?,?,?)",
                (conv_id, model, system_prompt, now, now),
            )
        return {"id": conv_id, "title": "New Conversation", "model": model,
                "system_prompt": system_prompt, "created_at": now, "updated_at": now}

    def get_conversation(self, conv_id: str) -> Optional[dict]:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM conversations WHERE id=?", (conv_id,)).fetchone()
        return dict(row) if row else None

    def list_conversations(self) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM conversations ORDER BY updated_at DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def update_conversation(self, conv_id: str, **kwargs):
        allowed = {"title", "model", "system_prompt"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}
        if not updates:
            return
        updates["updated_at"] = datetime.now().isoformat()
        set_clause = ", ".join(f"{k}=?" for k in updates)
        values = list(updates.values()) + [conv_id]
        with self._connect() as conn:
            conn.execute(f"UPDATE conversations SET {set_clause} WHERE id=?", values)

    def touch_conversation(self, conv_id: str):
        with self._connect() as conn:
            conn.execute(
                "UPDATE conversations SET updated_at=? WHERE id=?",
                (datetime.now().isoformat(), conv_id),
            )

    def delete_conversation(self, conv_id: str):
        with self._connect() as conn:
            conn.execute("DELETE FROM conversations WHERE id=?", (conv_id,))

    def clear_messages(self, conv_id: str):
        with self._connect() as conn:
            conn.execute("DELETE FROM messages WHERE conversation_id=?", (conv_id,))
        self.touch_conversation(conv_id)

    # ── messages ───────────────────────────────────────────────────────────────

    def add_message(
        self,
        conv_id: str,
        role: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> str:
        msg_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO messages (id, conversation_id, role, content, metadata, created_at) VALUES (?,?,?,?,?,?)",
                (msg_id, conv_id, role, content, json.dumps(metadata) if metadata else None, now),
            )
        self.touch_conversation(conv_id)
        return msg_id

    def get_messages(self, conv_id: str) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at ASC",
                (conv_id,),
            ).fetchall()
        result = []
        for row in rows:
            d = dict(row)
            if d.get("metadata"):
                try:
                    d["metadata"] = json.loads(d["metadata"])
                except Exception:
                    pass
            result.append(d)
        return result
